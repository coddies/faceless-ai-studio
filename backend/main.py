from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio
import os
import random
import json
import base64
import boto3
import edge_tts
from botocore.config import Config
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
import uuid
from typing import Any, Optional
from nova_client import call_groq, call_nova_pro, call_nova_canvas, call_nova_sonic

app = FastAPI(title="Faceless AI Studio API")
# Deployment Trigger: Updating environment variables for Vercel

def get_db():
    try:
        url = os.getenv("DATABASE_URL")
        if not url:
            print("WARNING: DATABASE_URL not set in environment or .env")
        return psycopg2.connect(url)
    except Exception as e:
        print(f"Database connection error: {e}")
        return None

@app.on_event("startup")
def startup_event():
    conn = get_db()
    if not conn:
        return
    try:
        with conn.cursor() as cur:
            cur.execute('''
                CREATE TABLE IF NOT EXISTS chats (
                    id SERIAL PRIMARY KEY,
                    session_id VARCHAR(255),
                    role VARCHAR(50),
                    message TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            ''')
            cur.execute('''
                CREATE TABLE IF NOT EXISTS scripts (
                    id SERIAL PRIMARY KEY,
                    title VARCHAR(255),
                    content TEXT,
                    tags TEXT,
                    keywords TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            ''')
            cur.execute('''
                CREATE TABLE IF NOT EXISTS projects (
                    id SERIAL PRIMARY KEY,
                    title VARCHAR(255),
                    thumbnail_url TEXT,
                    script TEXT,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            ''')
            # Ensure extended session/context columns exist on projects
            cur.execute("ALTER TABLE projects ADD COLUMN IF NOT EXISTS session_id VARCHAR(255);")
            cur.execute("ALTER TABLE projects ADD COLUMN IF NOT EXISTS seo_json TEXT;")
            cur.execute("ALTER TABLE projects ADD COLUMN IF NOT EXISTS thumbnail_prompt TEXT;")
            cur.execute("ALTER TABLE projects ADD COLUMN IF NOT EXISTS scenes_json TEXT;")
            cur.execute("ALTER TABLE projects ADD COLUMN IF NOT EXISTS voice_settings_json TEXT;")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_projects_session_id ON projects (session_id);")
        conn.commit()
        print("Database tables initialized successfully.")
    except Exception as e:
        print(f"Database initialization error: {e}")
    finally:
        conn.close()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class TopicRequest(BaseModel):
    query: str = ""

class ScriptRequest(BaseModel):
    topic: str
    tone: str = "Educational"
    length_words: int = 250

class AudioRequest(BaseModel):
    text: str
    voice_id: str = "Joanna"

class ChatRequest(BaseModel):
    message: str
    history: list = []
    session_id: str = "default_session"

class SceneRequest(BaseModel):
    script: str


class SessionUpdateRequest(BaseModel):
    session_id: Optional[str] = None
    title: Optional[str] = None
    script: Optional[str] = None
    description: Optional[str] = None
    seo: Optional[dict[str, Any]] = None
    thumbnail_url: Optional[str] = None
    thumbnail_prompt: Optional[str] = None
    scenes: Optional[list[str]] = None
    voice_settings: Optional[dict[str, Any]] = None


def generate_session_id() -> str:
    return f"session_{uuid.uuid4().hex}"


def _row_to_session_context(row: dict[str, Any]) -> dict[str, Any]:
    """Convert a projects row into a unified session context dict."""
    if not row:
        sid = generate_session_id()
        return {
            "session_id": sid,
            "title": "",
            "script": "",
            "description": "",
            "seo": None,
            "thumbnail_url": None,
            "thumbnail_prompt": None,
            "scenes": [],
            "voice_settings": None,
        }

    seo = None
    scenes = None
    voice_settings = None
    try:
        if row.get("seo_json"):
            seo = json.loads(row["seo_json"])
    except Exception:
        seo = None
    try:
        if row.get("scenes_json"):
            scenes = json.loads(row["scenes_json"])
    except Exception:
        scenes = None
    try:
        if row.get("voice_settings_json"):
            voice_settings = json.loads(row["voice_settings_json"])
    except Exception:
        voice_settings = None

    return {
        "session_id": row.get("session_id") or generate_session_id(),
        "title": row.get("title") or "",
        "script": row.get("script") or "",
        "description": row.get("description") or "",
        "seo": seo,
        "thumbnail_url": row.get("thumbnail_url"),
        "thumbnail_prompt": row.get("thumbnail_prompt"),
        "scenes": scenes or [],
        "voice_settings": voice_settings,
    }


def _upsert_session_context(update: SessionUpdateRequest) -> dict[str, Any]:
    """Create or update a unified session context backed by the projects table."""
    payload = update.model_dump(exclude_unset=True)
    session_id = payload.get("session_id") or generate_session_id()

    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM projects WHERE session_id = %s ORDER BY created_at DESC LIMIT 1",
                (session_id,),
            )
            existing = cur.fetchone()

            if existing:
                row = existing.copy()
            else:
                row = {
                    "session_id": session_id,
                    "title": "",
                    "script": "",
                    "description": "",
                    "thumbnail_url": None,
                    "seo_json": None,
                    "thumbnail_prompt": None,
                    "scenes_json": None,
                    "voice_settings_json": None,
                }

            # Basic fields
            if "title" in payload and payload["title"] is not None:
                row["title"] = payload["title"]
            if "script" in payload and payload["script"] is not None:
                row["script"] = payload["script"]
            if "description" in payload and payload["description"] is not None:
                row["description"] = payload["description"]
            if "thumbnail_url" in payload and payload["thumbnail_url"] is not None:
                row["thumbnail_url"] = payload["thumbnail_url"]
            if "thumbnail_prompt" in payload and payload["thumbnail_prompt"] is not None:
                row["thumbnail_prompt"] = payload["thumbnail_prompt"]

            # JSON/textified fields
            if "seo" in payload:
                row["seo_json"] = json.dumps(payload["seo"]) if payload["seo"] is not None else None
            if "scenes" in payload:
                row["scenes_json"] = json.dumps(payload["scenes"]) if payload["scenes"] is not None else None
            if "voice_settings" in payload:
                row["voice_settings_json"] = (
                    json.dumps(payload["voice_settings"]) if payload["voice_settings"] is not None else None
                )

            if existing:
                cur.execute(
                    """
                    UPDATE projects
                    SET session_id = %s,
                        title = %s,
                        thumbnail_url = %s,
                        script = %s,
                        description = %s,
                        seo_json = %s,
                        thumbnail_prompt = %s,
                        scenes_json = %s,
                        voice_settings_json = %s
                    WHERE id = %s
                    """,
                    (
                        session_id,
                        row["title"],
                        row["thumbnail_url"],
                        row["script"],
                        row["description"],
                        row.get("seo_json"),
                        row.get("thumbnail_prompt"),
                        row.get("scenes_json"),
                        row.get("voice_settings_json"),
                        row["id"],
                    ),
                )
            else:
                cur.execute(
                    """
                    INSERT INTO projects
                        (session_id, title, thumbnail_url, script, description,
                         seo_json, thumbnail_prompt, scenes_json, voice_settings_json)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING *
                    """,
                    (
                        session_id,
                        row["title"],
                        row["thumbnail_url"],
                        row["script"],
                        row["description"],
                        row.get("seo_json"),
                        row.get("thumbnail_prompt"),
                        row.get("scenes_json"),
                        row.get("voice_settings_json"),
                    ),
                )
                row = cur.fetchone()

        conn.commit()
        return _row_to_session_context(row)
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        print(f"Session upsert failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to update session context")
    finally:
        conn.close()


def _generate_scenes_from_script(script: str) -> dict[str, Any]:
    """Analyze script into key moments and generate matching images."""
    PLACEHOLDER_PNG_DATA_URL = (
        "data:image/png;base64,"
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO8Wk9cAAAAASUVORK5CYII="
    )

    # 1) AI analysis of the script to find 3-4 key moments
    analysis_prompt = f"""
Analyze this script and break it into 3 to 4 distinct key visual scenes.
For each scene, provide:
1. A concise natural description of what is happening (for the user).
2. A highly detailed visual prompt for an image generator (Nova Canvas/Stability).

Script:
{script}

Return ONLY a JSON list of objects in this exact format:
[
  {{
    "description": "Short scene description",
    "visual_prompt": "Detailed cinematic image prompt. Style: Cinematic, ultra-detailed, 16:9, no people, no text."
  }}
]
"""
    try:
        raw_analysis = call_nova_pro(analysis_prompt)
        cleaned = raw_analysis.replace('```json', '').replace('```', '').strip()
        start = cleaned.find('[')
        end = cleaned.rfind(']') + 1
        if start != -1 and end > start:
            cleaned = cleaned[start:end]
        scene_data = json.loads(cleaned)
    except Exception as e:
        print(f"Script analysis failed: {e}")
        # Fallback to simple segmentation if AI analysis fails
        segments = [s.strip() for s in script.split('.') if s.strip()][:3]
        scene_data = [{"description": s, "visual_prompt": f"Cinematic shot of {s}, high quality, no text"} for s in segments]

    # 2) Generate images for each scene
    final_scenes = []
    warnings = []
    
    for idx, scene_item in enumerate(scene_data[:4]):
        v_prompt = scene_item.get("visual_prompt", "Cinematic establishing shot")
        desc = scene_item.get("description", "Key moment")
        try:
            img_b64 = call_nova_canvas(v_prompt)
            final_scenes.append({
                "id": idx + 1,
                "text": desc,
                "img": img_b64
            })
        except Exception as e:
            warnings.append(f"Scene {idx+1} image generation failed: {str(e)}")
            final_scenes.append({
                "id": idx + 1,
                "text": desc,
                "img": PLACEHOLDER_PNG_DATA_URL
            })

    return {"scenes": final_scenes, "warnings": warnings}

@app.get("/api/get-topics")
async def get_topics():
    prompt = """You are a creative YouTube strategist. Generate 6 trending YouTube video topics across different genres (Music, Science, Tech, History, etc).
Return ONLY a JSON list of objects in this exact format, with NO markdown formatting, just the raw JSON:
[
  {
    "id": "short-slug",
    "title": "Exciting Video Title",
    "description": "A 2-sentence engaging description.",
    "category": "Category Name",
    "image": "https://images.unsplash.com/photo-1542281286-9e0a16bb7366?auto=format&fit=crop&q=80&w=800"
  }
]
Use valid, high-quality Unsplash image URLs for the 'image' field. Return nothing but the JSON."""
    try:
        raw = call_nova_pro(prompt)
        cleaned = raw.replace('```json', '').replace('```', '').strip()
        # Find json array boundaries
        start = cleaned.find('[')
        end = cleaned.rfind(']') + 1
        if start != -1 and end > start:
            cleaned = cleaned[start:end]
            
        data = json.loads(cleaned)
        return {"topics": data}
    except Exception as e:
        print(f"Error generating topics: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch trending topics using AI.")

@app.get("/api/search-topics")
async def search_topics(q: str = ""):
    if not q.strip():
        return await get_topics()
    prompt = f"""You are a creative YouTube strategist. Generate 3 YouTube video topics strictly related to this search query: "{q}".
Return ONLY a JSON list of objects in this exact format, with NO markdown formatting, just the raw JSON:
[
  {{
    "id": "short-slug",
    "title": "Exciting {q} Video Title",
    "description": "A 2-sentence engaging description.",
    "category": "Search Result",
    "image": "https://images.unsplash.com/photo-1542281286-9e0a16bb7366?auto=format&fit=crop&q=80&w=800"
  }}
]
Use valid, high-quality Unsplash image URLs for the 'image' field. Return nothing but the JSON."""
    try:
        raw = call_nova_pro(prompt)
        cleaned = raw.replace('```json', '').replace('```', '').strip()
        start = cleaned.find('[')
        end = cleaned.rfind(']') + 1
        if start != -1 and end > start:
            cleaned = cleaned[start:end]
            
        data = json.loads(cleaned)
        return {"topics": data, "is_search": True}
    except Exception as e:
        print(f"Error searching topics: {e}")
        raise HTTPException(status_code=500, detail="Failed to search topics using AI.")

@app.get("/api/random-topic")
async def random_topic():
    prompt = """You are a creative YouTube strategist. Generate 1 random but highly engaging YouTube video topic.
Return ONLY a JSON object in this exact format, with NO markdown formatting, just the raw JSON:
{
  "id": "short-slug",
  "title": "Exciting Random Video Title",
  "description": "A 2-sentence engaging description.",
  "category": "Random Selection",
  "image": "https://images.unsplash.com/photo-1542281286-9e0a16bb7366?auto=format&fit=crop&q=80&w=800"
}
Use valid Unsplash image URL for 'image'. Return nothing but the JSON."""
    try:
        raw = call_nova_pro(prompt)
        cleaned = raw.replace('```json', '').replace('```', '').strip()
        start = cleaned.find('{')
        end = cleaned.rfind('}') + 1
        if start != -1 and end > start:
            cleaned = cleaned[start:end]
            
        data = json.loads(cleaned)
        # If it returned a list, grab the first one
        if isinstance(data, list) and len(data) > 0:
            data = data[0]
        return {"topic": data}
    except Exception as e:
        print(f"Error generating random topic: {e}")
        raise HTTPException(status_code=500, detail="Failed to pick random topic using AI.")


class FullVideoRequest(BaseModel):
    title: str
    session_id: Optional[str] = None

class RegenerateThumbnailRequest(BaseModel):
    title: str
    style: str = "cinematic"


@app.post("/api/generate-full-video")
async def generate_full_video(req: FullVideoRequest):
    title = (req.title or "").strip() or "Untitled Video"
    slug = title.replace(" ", "")[:20]
    session_id = req.session_id or generate_session_id()

    prompt = f"""You are a professional YouTube SEO expert and viral content strategist.
For the YouTube video topic: "{title}"

Generate the following in VALID JSON format only (no extra text, no markdown):

{{
  "title": "A powerful, curiosity-driven YouTube title with numbers or emotions (max 70 chars)",
  "description": "A full SEO-optimized YouTube description of 200-250 words. Include: 1) Hook sentence, 2) What viewers will learn (3-5 points), 3) Call to action to subscribe, 4) Relevant keywords naturally placed. Make it engaging and professional.",
  "tags": ["#tag1", "#tag2", "#tag3", "#tag4", "#tag5", "#tag6", "#tag7", "#tag8", "#tag9", "#tag10"],
  "keywords": ["keyword1", "keyword2", "keyword3", "keyword4", "keyword5", "keyword6", "keyword7", "keyword8", "keyword9", "keyword10"],
  "script_content": "A 200 word engaging YouTube script with hook, main content, and call to action."
}}

Rules:
- Title must be clickbait but accurate (use numbers, questions, or power words)
- Description must be 200+ words with proper paragraphs
- Include exactly 10 tags with # symbol
- Include exactly 10 SEO keywords without #
- All content must be unique and specific to the topic"""

    try:
        text_response = call_nova_pro(prompt)
        cleaned_response = text_response.replace('```json', '').replace('```', '').strip()

        start = cleaned_response.find('{')
        end = cleaned_response.rfind('}') + 1
        if start != -1 and end > start:
            cleaned_response = cleaned_response[start:end]

        data = json.loads(cleaned_response)

        thumb_prompt = f"Professional YouTube thumbnail for: {title}, cinematic lighting, dramatic colors, no people, no faces, no text, 8K quality, highly detailed"
        thumbnail_url = call_nova_canvas(thumb_prompt)
        
        script_content_val = data.get("script_content", f"In this video, we dive deep into {title}.")
        desc_val = data.get("description", f"In this video, we explore everything about {title}.")
        title_val = data.get("title", f"The Untold Truth About {title}")

        tags_val = data.get("tags", ["#Education", "#Trending", "#AI", f"#{slug}"])
        keywords_val = data.get("keywords", [slug, "explained", "deep dive", "viral", "tutorial"])

        # Persist unified session context
        session_ctx = _upsert_session_context(
            SessionUpdateRequest(
                session_id=session_id,
                title=title_val,
                script=script_content_val,
                description=desc_val,
                thumbnail_url=thumbnail_url,
                thumbnail_prompt=thumb_prompt,
                seo={
                    "tags": tags_val,
                    "keywords": keywords_val,
                    "description": desc_val,
                    "seo_title": title_val,
                },
                scenes=[],
                voice_settings={"suggested_profile": "nova_energetic", "estimated_duration": "1:45"},
            )
        )

        # Return backwards-compatible shape plus session context id
        return {
            "session_id": session_ctx["session_id"],
            "title": title_val,
            "description": desc_val,
            "tags": tags_val,
            "keywords": keywords_val,
            "thumbnail_url": thumbnail_url,
            "scenes": [],
            "script_content": script_content_val,
            "estimated_duration": "1:45",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/regenerate-thumbnail")
async def regenerate_thumbnail(req: RegenerateThumbnailRequest):
    prompt = f"Professional YouTube thumbnail for: {req.title}, style: {req.style}, cinematic lighting, dramatic colors, no people, no faces, no text, 8K quality"
    try:
        thumbnail_url = call_nova_canvas(prompt)
        return {
            "thumbnail_url": thumbnail_url,
            "style": req.style,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/generate-from-title")
async def generate_from_title(req: FullVideoRequest):
    """
    Orchestrated endpoint: from a single title, generate SEO, script, thumbnail, scenes,
    and persist everything into a unified session.
    """
    title = (req.title or "").strip() or "Untitled Video"
    slug = title.replace(" ", "")[:20]
    session_id = req.session_id or generate_session_id()

    # 1) Generate SEO + script (reuse Nova Pro logic)
    prompt = f"""You are a professional YouTube SEO expert and viral content strategist.
For the YouTube video topic: "{title}"

Generate the following in VALID JSON format only (no extra text, no markdown):

{{
  "title": "A powerful, curiosity-driven YouTube title with numbers or emotions (max 70 chars)",
  "description": "A full SEO-optimized YouTube description of 200-250 words. Include: 1) Hook sentence, 2) What viewers will learn (3-5 points), 3) Call to action to subscribe, 4) Relevant keywords naturally placed. Make it engaging and professional.",
  "tags": ["#tag1", "#tag2", "#tag3", "#tag4", "#tag5", "#tag6", "#tag7", "#tag8", "#tag9", "#tag10"],
  "keywords": ["keyword1", "keyword2", "keyword3", "keyword4", "keyword5", "keyword6", "keyword7", "keyword8", "keyword9", "keyword10"],
  "script_content": "A 200 word engaging YouTube script with hook, main content, and call to action."
}}

Rules:
- Title must be clickbait but accurate (use numbers, questions, or power words)
- Description must be 200+ words with proper paragraphs
- Include exactly 10 tags with # symbol
- Include exactly 10 SEO keywords without #
- All content must be unique and specific to the topic"""

    try:
        text_response = call_nova_pro(prompt)
        cleaned_response = text_response.replace("```json", "").replace("```", "").strip()

        start = cleaned_response.find("{")
        end = cleaned_response.rfind("}") + 1
        if start != -1 and end > start:
            cleaned_response = cleaned_response[start:end]

        data = json.loads(cleaned_response)

        thumb_prompt = (
            f"Professional YouTube thumbnail for: {title}, cinematic lighting, dramatic colors, "
            f"no people, no faces, no text, 8K quality, highly detailed"
        )
        thumbnail_url = call_nova_canvas(thumb_prompt)

        script_content_val = data.get("script_content", f"In this video, we dive deep into {title}.")
        desc_val = data.get("description", f"In this video, we explore everything about {title}.")
        title_val = data.get("title", f"The Untold Truth About {title}")

        tags_val = data.get("tags", ["#Education", "#Trending", "#AI", f"#{slug}"])
        keywords_val = data.get("keywords", [slug, "explained", "deep dive", "viral", "tutorial"])

        # 2) Analyze script and generate structured scenes
        scenes_result = _generate_scenes_from_script(script_content_val)

        # 3) Suggested voiceover profile (simple heuristic for now)
        voice_settings = {"suggested_profile": "nova_energetic", "estimated_duration": "1:45"}

        # 4) Persist unified session context
        session_ctx = _upsert_session_context(
            SessionUpdateRequest(
                session_id=session_id,
                title=title_val,
                script=script_content_val,
                description=desc_val,
                thumbnail_url=thumbnail_url,
                thumbnail_prompt=thumb_prompt,
                seo={
                    "tags": tags_val,
                    "keywords": keywords_val,
                    "description": desc_val,
                    "seo_title": title_val,
                },
                scenes=scenes_result["scenes"],
                voice_settings=voice_settings,
            )
        )

        # 5) Response combines full video kit with extra orchestration metadata
        return {
            "session_id": session_ctx["session_id"],
            "title": title_val,
            "description": desc_val,
            "tags": tags_val,
            "keywords": keywords_val,
            "thumbnail_url": thumbnail_url,
            "thumbnail_prompt": thumb_prompt,
            "scenes": scenes_result["scenes"],
            "scene_prompts": scenes_result.get("scene_prompts", []),
            "warnings": scenes_result["warnings"],
            "script_content": script_content_val,
            "voiceover": voice_settings,
            "estimated_duration": voice_settings.get("estimated_duration", "1:45"),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/generate-script")
async def generate_script(req: ScriptRequest):
    prompt = f"""You are a professional YouTube content creator.

The user wants creative content for: "{req.topic}"
Tone/Style: {req.tone}
Target length: {req.length_words} words

Instructions:
- If it's a VIDEO TOPIC → write a YouTube video script with [HOOK], [MAIN CONTENT], [CALL TO ACTION] sections
- If it's a SONG/LULLABY/LYRICS → write proper song lyrics with verses, chorus, bridge
- If it's a STORY/HORROR/NARRATIVE → write an engaging story script
- If it's a TUTORIAL/HOW-TO → write step-by-step presentation script
- Detect the content type from the topic automatically
- DO NOT output JSON, markdown code blocks, or structured data
- Output ONLY the clean script/lyrics/story text, ready to read
- Make it creative, engaging, and ready to use directly

Write the complete {req.tone} content now:"""

    try:
        script_text = call_nova_pro(prompt)
        # Strip any accidental JSON or markdown
        clean = script_text.strip()
        if clean.startswith('{') or clean.startswith('```'):
            # AI returned JSON anyway, extract script_content if possible
            try:
                cleaned = clean.replace('```json','').replace('```','').strip()
                start = cleaned.find('{')
                end = cleaned.rfind('}') + 1
                if start != -1 and end > start:
                    data = json.loads(cleaned[start:end])
                    clean = data.get('script_content', clean)
            except Exception:
                pass
                
        final_title = f"{req.topic} — {req.tone} Script"
        
        # Save to scripts table
        conn = get_db()
        if conn:
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO scripts (title, content, tags, keywords) VALUES (%s, %s, %s, %s)",
                        (final_title, clean, "", "")
                    )
                conn.commit()
            except Exception as e:
                print(f"Failed to save script to DB: {e}")
            finally:
                conn.close()
                
        return {
            "title": final_title,
            "script_content": clean,
            "estimated_duration": "2:00"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class SeoRequest(BaseModel):
    topic: str

@app.post("/api/generate-seo")
async def generate_seo(req: SeoRequest):
    prompt = f"""You are a YouTube SEO expert with 10+ years of experience growing viral channels.

Topic: "{req.topic}"

Generate ALL of the following in VALID JSON only (no extra text, no markdown):

{{
  "viral_title": "Short, punchy title, max 60 chars, NO clickbait nonsense",
  "seo_title": "Clean keyword-focused title, max 60 chars",
  "description": "Natural flowing description of 150-200 words. NO timestamps, NO 'you'll learn 5 things', just an engaging narrative introduction.",
  "tags": ["#tag1","#tag2","#tag3", "... exactly 15-20 relevant hashtags"],
  "keywords": ["kw1","kw2","kw3", "... exactly 15-20 clean keywords"]
}}

Rules:
- Title must be professional and engaging (Example: 'Kids Lullaby - Sweet Dreams Little One')
- Description MUST be 150-200 words exactly, no lists or bullet points
- tags and keywords must be arrays of exactly 15 to 20 items each.
- All content must be unique and specific to the topic."""

    try:
        raw = call_nova_pro(prompt)
        cleaned = raw.replace('```json', '').replace('```', '').strip()

        # Extract JSON object from the response
        start = cleaned.find('{')
        end = cleaned.rfind('}') + 1
        if start != -1 and end > start:
            cleaned = cleaned[start:end]

        # Fix control characters inside JSON string values (newlines, tabs, etc.)
        import re
        # Replace literal newlines/carriage returns within JSON string values
        def fix_json_string(s):
            # Replace invalid control characters inside strings with space or escaped version
            result = []
            in_string = False
            i = 0
            while i < len(s):
                c = s[i]
                if c == '"' and (i == 0 or s[i-1] != '\\'):
                    in_string = not in_string
                    result.append(c)
                elif in_string and c == '\n':
                    result.append('\\n')
                elif in_string and c == '\r':
                    result.append('\\r')
                elif in_string and c == '\t':
                    result.append('\\t')
                else:
                    result.append(c)
                i += 1
            return ''.join(result)

        cleaned = fix_json_string(cleaned)

        try:
            data = json.loads(cleaned)
        except Exception:
            # Last resort: use regex to extract individual fields
            def extract_field(text, key):
                pattern = rf'"{key}"\s*:\s*"(.*?)"(?=\s*[,}}])'
                m = re.search(pattern, text, re.DOTALL)
                return m.group(1).strip() if m else ""

            slug = req.topic.replace(' ', '')
            return {
                "viral_title": extract_field(raw, "viral_title") or f"The Shocking Truth About {req.topic}",
                "seo_title": extract_field(raw, "seo_title") or f"{req.topic} - Complete Guide",
                "description": extract_field(raw, "description") or f"Everything about {req.topic}",
                "tags": [f"#{slug}", "#YouTube", "#Education", "#Trending", "#Viral"],
                "keywords": [req.topic, "youtube", "tutorial", "guide", "tips"]
            }

        slug = req.topic.replace(' ', '')
        return {
            "viral_title": data.get("viral_title", f"The Shocking Truth About {req.topic}"),
            "seo_title": data.get("seo_title", f"{req.topic} - Complete Guide"),
            "description": data.get("description", f"Everything about {req.topic}"),
            "tags": data.get("tags", [f"#{slug}", "#YouTube", "#Education"]),
            "keywords": data.get("keywords", [req.topic, "youtube", "tutorial"])
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@app.post("/api/chat")
async def chat(req: ChatRequest):
    history_text = ""
    for turn in req.history[-6:]:
        role_label = "User" if turn.get("role") == "user" else "Nova AI"
        history_text += f"{role_label}: {turn.get('content', '')}\n"

    full_prompt = f"""You are Nova AI, a friendly YouTube content creation assistant. You have expertise in YouTube growth, scripts, SEO, niche strategy, thumbnails, and faceless channels.

Personality:
- Talk naturally and casually, like a smart helpful friend
- When someone says "hey", "hi", "hello" — just greet back warmly and ask what you can help with
- For YouTube-related questions: give specific, actionable, expert advice
- For off-topic questions: answer briefly and naturally, then gently mention you can also help with their YouTube channel
- Never say robotic phrases like "I'm specialized in..." — just be natural
- Keep responses concise unless detail is needed

{f'Previous conversation:{chr(10)}{history_text}' if history_text else ''}
User: {req.message}
Nova AI:"""

    try:
        reply = call_nova_pro(full_prompt)
        reply_strip = reply.strip()
        
        # Save to chats table
        conn = get_db()
        if conn:
            try:
                with conn.cursor() as cur:
                    # Save user message
                    cur.execute(
                        "INSERT INTO chats (session_id, role, message) VALUES (%s, %s, %s)",
                        (req.session_id, "user", req.message)
                    )
                    # Save AI reply
                    cur.execute(
                        "INSERT INTO chats (session_id, role, message) VALUES (%s, %s, %s)",
                        (req.session_id, "assistant", reply_strip)
                    )
                conn.commit()
            except Exception as e:
                print(f"Failed to save chat to DB: {e}")
            finally:
                conn.close()
                
        return {"reply": reply_strip}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/generate-audio")
async def generate_audio(req: AudioRequest):
    """
    Generate audio using Bedrock's Nova Sonic (us-east-1) as primary, with a 
    direct fallback to Edge-TTS for stability and high quality.
    """
    # 1. Try NOVA SONIC (Bedrock us-east-1)
    try:
        print("[main] Attempting Nova Sonic (us-east-1)...")
        # We use a custom call to ensure we target us-east-1 specifically
        audio_b64 = call_nova_sonic(req.text)
        if audio_b64:
            return {
                "audio_base64": audio_b64, 
                "format": "mp3",
                "engine_used": "nova-sonic"
            }
    except Exception as e:
        print(f"[main] Nova Sonic failed: {e}. Switching to Edge-TTS fallback...")

    # 2. FINAL EMERGENCY FALLBACK: EDGE-TTS (No Keys/Permissions Needed)
    try:
        print("[main] Attempting Edge-TTS emergency fallback...")
        # Map some common voice IDs to high-quality Edge-TTS voices
        voice = "en-US-EmmaMultilingualNeural" 
        if "Matthew" in (req.voice_id or ""):
            voice = "en-US-ChristopherNeural"
        
        async def generate_edge_audio():
            communicate = edge_tts.Communicate(req.text[:3000], voice)
            audio_data = b""
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_data += chunk["data"]
            return audio_data

        edge_audio_bytes = await generate_edge_audio()
        if edge_audio_bytes:
            audio_b64 = base64.b64encode(edge_audio_bytes).decode('utf-8')
            print("[main] Edge-TTS emergency fallback success ✅")
            return {
                "audio_base64": audio_b64, 
                "format": "mp3",
                "engine_used": "edge-tts",
                "status": "fallback_success"
            }
    except Exception as e:
        print(f"[main] Edge-TTS failed: {e}")

    # Final Failure
    error_msg = "All audio services failed. Please check your internet connection."
    print(f"[main] Global Audio Failure: {error_msg}")
    raise HTTPException(status_code=503, detail=error_msg)


@app.post("/api/generate-scenes")
async def generate_scenes(req: SceneRequest):
    try:
        script = req.script if req.script else "Cinematic nature landscapes"
        return _generate_scenes_from_script(script)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/session/current")
async def get_session_current(session_id: Optional[str] = None):
    """Fetch the latest unified session context, or a specific one by session_id."""
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if session_id:
                cur.execute(
                    "SELECT * FROM projects WHERE session_id = %s ORDER BY created_at DESC LIMIT 1",
                    (session_id,),
                )
            else:
                cur.execute("SELECT * FROM projects ORDER BY created_at DESC LIMIT 1")
            row = cur.fetchone()

            if row and not row.get("session_id"):
                # Attach a new session_id to legacy rows
                new_session_id = generate_session_id()
                cur.execute(
                    "UPDATE projects SET session_id = %s WHERE id = %s",
                    (new_session_id, row["id"]),
                )
                conn.commit()
                row["session_id"] = new_session_id

            ctx = _row_to_session_context(row or {})
            return ctx
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching session context: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch session context")
    finally:
        conn.close()


@app.post("/api/session/update")
async def update_session(req: SessionUpdateRequest):
    """Create or update session context and return the latest snapshot."""
    try:
        ctx = _upsert_session_context(req)
        return ctx
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/chat-history")
async def get_chat_history():
    conn = get_db()
    if not conn:
        return {"grouped": {}}
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT 
                    session_id, 
                    MAX(timestamp) as last_activity,
                    (SELECT message FROM chats c2 WHERE c2.session_id = c.session_id AND role = 'user' ORDER BY timestamp ASC LIMIT 1) as snippet
                FROM chats c
                GROUP BY session_id
                ORDER BY last_activity DESC
            """)
            rows = cur.fetchall()
            
            grouped = {
                "Today": [],
                "Yesterday": [],
                "Last 7 Days": [],
                "Older": []
            }
            
            now = datetime.now()
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            yesterday_start = today_start - timedelta(days=1)
            week_start = today_start - timedelta(days=7)
            
            for r in rows:
                snippet = r['snippet'] or "Empty Chat"
                if len(snippet) > 30:
                    snippet = snippet[:30] + "..."
                
                item = {
                    "session_id": r['session_id'],
                    "snippet": snippet,
                    "timestamp": str(r['last_activity'])
                }
                
                t = r['last_activity']
                if t >= today_start:
                    grouped["Today"].append(item)
                elif t >= yesterday_start:
                    grouped["Yesterday"].append(item)
                elif t >= week_start:
                    grouped["Last 7 Days"].append(item)
                else:
                    grouped["Older"].append(item)
                    
            return {"grouped": grouped}
    except Exception as e:
        print(f"Error fetching chat history: {e}")
        return {"grouped": {}}
    finally:
        conn.close()

@app.get("/api/chat-session/{session_id}")
async def get_chat_session(session_id: str):
    conn = get_db()
    if not conn:
        return {"messages": []}
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM chats WHERE session_id = %s ORDER BY timestamp ASC", (session_id,))
            rows = cur.fetchall()
            for r in rows:
                if r.get('timestamp'):
                    r['timestamp'] = str(r['timestamp'])
            return {"messages": rows}
    except Exception as e:
        print(f"Error fetching session: {e}")
        return {"messages": []}
    finally:
        conn.close()

@app.delete("/api/chat-session/{session_id}")
async def delete_chat_session(session_id: str):
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="DB Connection Failed")
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM chats WHERE session_id = %s", (session_id,))
        conn.commit()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.get("/api/saved-scripts")
async def get_saved_scripts():
    conn = get_db()
    if not conn:
        return {"scripts": []}
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM scripts ORDER BY created_at DESC")
            rows = cur.fetchall()
            for r in rows:
                if r.get('created_at'):
                    r['created_at'] = str(r['created_at'])
            return {"scripts": rows}
    except Exception as e:
        print(f"Error fetching scripts: {e}")
        return {"scripts": []}
    finally:
        conn.close()

@app.get("/api/projects")
async def get_projects():
    conn = get_db()
    if not conn:
        return {"projects": []}
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM projects ORDER BY created_at DESC")
            rows = cur.fetchall()
            for r in rows:
                if r.get('created_at'):
                    r['created_at'] = str(r['created_at'])
            return {"projects": rows}
    except Exception as e:
        print(f"Error fetching projects: {e}")
        return {"projects": []}
    finally:
        conn.close()

@app.delete("/api/clear-history")
async def clear_history(session_id: str = "default_session"):
    # This remains for backward compatibility if needed, though we primarily use DELETE /api/chat-session/{session_id} now
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="DB Connection Failed")
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM chats WHERE session_id = %s", (session_id,))
        conn.commit()
        return {"status": "success", "message": "Chat history cleared."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "environment": os.getenv("VERCEL", "local")}

# Frontend Serving Logic (Optimized for Windows/Local/Vercel)
# 1. Determine absolute root path of the project
current_dir = os.path.dirname(os.path.abspath(__file__))
# 2. Check if we're in 'backend' or 'api' subfolders
if os.path.basename(current_dir) in ['backend', 'api']:
    project_root = os.path.dirname(current_dir)
else:
    project_root = current_dir

frontend_path = os.path.join(project_root, "frontend")

if not os.path.exists(frontend_path):
    print(f"CRITICAL WARNING: Frontend folder not found at {frontend_path}")

app.mount("/static", StaticFiles(directory=frontend_path), name="static")

@app.get("/")
async def serve_frontend():
    index_file = os.path.join(frontend_path, "index.html")
    if not os.path.exists(index_file):
        raise HTTPException(status_code=404, detail=f"index.html not found in {frontend_path}")
    return FileResponse(index_file)

@app.get("/{file_path:path}")
async def serve_static_root(file_path: str):
    file = os.path.join(frontend_path, file_path)
    if os.path.exists(file):
        return FileResponse(file)
    raise HTTPException(status_code=404)

if __name__ == "__main__":
    import uvicorn
    # Move to port 5106 to avoid common Windows conflicts like 8000/5000
    print("\n" + "="*50)
    print("🚀 NOVA AI STUDIO IS STARTING!")
    print("🔗 ACCESS THE FRONTEND AT: http://127.0.0.1:5106")
    print("="*50 + "\n")
    uvicorn.run("main:app", host="127.0.0.1", port=5106, reload=False)
