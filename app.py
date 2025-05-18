import streamlit as st
import sqlite3
import os
import requests
import time
import logging
from datetime import datetime
from PIL import Image
import io
import base64
import random

# Set up logging
logging.basicConfig(filename='image_generator.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Set up page configuration
st.set_page_config(
    page_title="Stable Diffusion Image Generator",
    page_icon="🖼️",
    layout="wide"
)

# Create directory for storing images if it doesn't exist
if not os.path.exists("generated_images"):
    os.makedirs("generated_images")

# Database setup
def init_db():
    with sqlite3.connect('image_generator.db') as conn:
        c = conn.cursor()
        c.execute('''
        CREATE TABLE IF NOT EXISTS prompts
        (id INTEGER PRIMARY KEY AUTOINCREMENT,
        prompt TEXT,
        expected_style TEXT,
        filename TEXT,
        created_at TIMESTAMP,
        score INTEGER,
        feedback TEXT)
        ''')
        c.execute('CREATE INDEX IF NOT EXISTS idx_created_at ON prompts (created_at)')
        conn.commit()

# Initialize database
init_db()

# Validate prompt
def validate_prompt(prompt):
    if not prompt or len(prompt.strip()) == 0:
        st.error("Prompt cannot be empty.")
        return None
    if len(prompt) > 500:
        st.error("Prompt is too long (max 500 characters).")
        return None
    cleaned_prompt = " ".join(prompt.strip().split())
    return cleaned_prompt

# Hugging Face API for Stable Diffusion
def generate_image(prompt, style=None):
    logging.info(f"Generating image for prompt: {prompt}, style: {style}")
    API_TOKEN = st.secrets.get("HUGGING_FACE_API_TOKEN")
    if not API_TOKEN:
        st.error("Hugging Face API token not configured. Using demo mode.")
        logging.warning("API token missing, switching to demo mode")
        st.session_state.demo_mode = True

    if st.session_state.get('demo_mode', True):
        with st.spinner(f"Generating image for: {prompt}..."):
            time.sleep(3)
        logging.info("Demo mode: Returning placeholder image")
        return Image.new('RGB', (512, 512), color=(73, 109, 137))
    else:
        headers = {"Authorization": f"Bearer {API_TOKEN}"}
        if style == "cyberpunk":
            model_id = "black-forest-labs/FLUX.1-dev"
        elif style == "cartoon":
            model_id = "black-forest-labs/FLUX.1-dev"
        else:
            model_id = "stabilityai/stable-diffusion-xl-base-1.0"
        
        API_URL = f"https://api-inference.huggingface.co/models/{model_id}"
        for attempt in range(3):
            with st.spinner(f"Generating image for: {prompt} (Attempt {attempt + 1}/3)..."):
                response = requests.post(
                    API_URL,
                    headers=headers,
                    json={"inputs": prompt}
                )
            if response.status_code == 200:
                logging.info(f"Image generated successfully for prompt: {prompt}")
                return Image.open(io.BytesIO(response.content))
            elif response.status_code == 429:
                logging.warning(f"Rate limit hit on attempt {attempt + 1}, retrying...")
                time.sleep(2 ** attempt)
            else:
                break
        try:
            error_msg = response.json().get("error", "Unknown error")
            logging.error(f"API error: {error_msg}, Status code: {response.status_code}")
            st.error(f"Failed to generate image: {error_msg} (Status code: {response.status_code})")
        except:
            logging.error(f"Non-JSON API error, Status code: {response.status_code}")
            st.error(f"Failed to generate image: API error (Status code: {response.status_code})")
        return None

# Save image to disk and database
def save_image(image, prompt, expected_style):
    if image.size[0] > 4096 or image.size[1] > 4096:
        st.error("Image dimensions are too large.")
        return None, None
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"generated_images/image_{timestamp}.png"
    image.save(filename)
    with sqlite3.connect('image_generator.db') as conn:
        c = conn.cursor()
        c.execute(
            "INSERT INTO prompts (prompt, expected_style, filename, created_at) VALUES (?, ?, ?, ?)",
            (prompt, expected_style, filename, datetime.now())
        )
        conn.commit()
        c.execute("SELECT last_insert_rowid()")
        prompt_id = c.fetchone()[0]
    return filename, prompt_id

# Delete image
def delete_image(prompt_id, filename):
    if os.path.exists(filename):
        os.remove(filename)
    with sqlite3.connect('image_generator.db') as conn:
        c = conn.cursor()
        c.execute("DELETE FROM prompts WHERE id = ?", (prompt_id,))
        conn.commit()

# Load image from file
def load_image(filename):
    if os.path.exists(filename):
        return Image.open(filename)
    return None

# Get all prompts from database
@st.cache_data(ttl=60)
def get_all_prompts():
    with sqlite3.connect('image_generator.db') as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM prompts ORDER BY created_at DESC")
        prompts = [dict(row) for row in c.fetchall()]
    return prompts

# Update image score and feedback
def update_evaluation(prompt_id, score, feedback):
    if prompt_id is None:
        st.error("Cannot submit rating: No prompt ID available.")
        return
    with sqlite3.connect('image_generator.db') as conn:
        c = conn.cursor()
        c.execute(
            "UPDATE prompts SET score = ?, feedback = ? WHERE id = ?",
            (score, feedback, prompt_id)
        )
        conn.commit()

# Function to get image as base64 for display
def get_image_base64(image_path):
    base_dir = os.path.abspath("generated_images")
    full_path = os.path.abspath(image_path)
    if not full_path.startswith(base_dir) or not os.path.exists(full_path):
        return None
    with open(full_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode('utf-8')

# Rate limiting
def check_rate_limit():
    if 'last_request_time' not in st.session_state:
        st.session_state.last_request_time = 0
        st.session_state.request_count = 0
    
    current_time = time.time()
    if current_time - st.session_state.last_request_time > 60:
        st.session_state.request_count = 0
    
    st.session_state.request_count += 1
    st.session_state.last_request_time = current_time
    
    if st.session_state.request_count > 5:
        st.error("Rate limit exceeded. Please wait a minute before generating another image.")
        return False
    return True

# Main app
def main():
    # Reset session state to avoid stale widget states
    if 'reset_session' not in st.session_state:
        st.session_state.clear()
        st.session_state.reset_session = True
        st.session_state.demo_mode = False
        st.session_state.last_request_time = 0
        st.session_state.request_count = 0

    st.title("🖼️ Stable Diffusion Image Generator")
    style_options = ["realistic", "cyberpunk", "cartoon"]
    tab1, tab2, tab3, tab4 = st.tabs(["Generate Images", "Image Gallery", "Prompt History", "Evaluation Report"])

    with tab1:
        st.header("Generate a New Image")
        with st.form("prompt_form"):
            prompt = st.text_area("Enter your prompt:", 
                                 placeholder="Describe the image you want to generate...",
                                 key="prompt_input")
            expected_style = st.selectbox("Select expected style:", style_options)
            submitted = st.form_submit_button("Generate Image")
            if submitted:
                cleaned_prompt = validate_prompt(prompt)
                if cleaned_prompt and check_rate_limit():
                    image = generate_image(cleaned_prompt, expected_style)
                    if image:
                        filename, prompt_id = save_image(image, cleaned_prompt, expected_style)
                        if filename:
                            st.success("Image generated successfully!")
                            st.image(image, caption=f"Generated image for: {cleaned_prompt}", use_container_width=True)
                            st.session_state['latest_prompt_id'] = prompt_id

        if 'latest_prompt_id' in st.session_state and st.session_state['latest_prompt_id']:
            st.subheader("Rate this generation")
            with st.form("rating_form"):
                col1, col2 = st.columns(2)
                with col1:
                    score = st.slider("Match to prompt (1-10):", 1, 10, 5)
                with col2:
                    feedback = st.text_input("Feedback (optional):")
                if st.form_submit_button("Submit Rating"):
                    update_evaluation(st.session_state['latest_prompt_id'], score, feedback)
                    st.success("Rating submitted successfully!")
                    del st.session_state['latest_prompt_id']

    with tab2:
        st.header("Image Gallery")
        prompts = get_all_prompts()
        if not prompts:
            st.info("No images generated yet. Create your first image in the 'Generate Images' tab!")
        else:
            filter_style = st.selectbox("Filter by style:", ["All"] + style_options, key="gallery_filter")
            filtered_prompts = prompts if filter_style == "All" else [p for p in prompts if p["expected_style"] == filter_style]

            images_per_page = 9
            total_pages = (len(filtered_prompts) + images_per_page - 1) // images_per_page
            page = st.number_input("Page", min_value=1, max_value=max(1, total_pages), value=1, step=1)
            start_idx = (page - 1) * images_per_page
            end_idx = start_idx + images_per_page
            paginated_prompts = filtered_prompts[start_idx:end_idx]

            cols = st.columns(3)
            for i, prompt_data in enumerate(paginated_prompts):
                with cols[i % 3]:
                    img_b64 = get_image_base64(prompt_data["filename"])
                    if img_b64:
                        st.image(prompt_data["filename"], 
                                caption=prompt_data["prompt"][:50] + "..." if len(prompt_data["prompt"]) > 50 else prompt_data["prompt"],
                                use_container_width=True)
                        st.caption(f"Style: {prompt_data['expected_style']}")
                        if prompt_data["score"]:
                            st.caption(f"Score: {prompt_data['score']}/10")
                        with open(prompt_data["filename"], "rb") as file:
                            st.download_button(
                                label="Download Image",
                                data=file,
                                file_name=prompt_data["filename"].split("/")[-1],
                                mime="image/png",
                                key=f"download_gallery_{prompt_data['id']}"
                            )
                        if st.button("Delete", key=f"delete_{prompt_data['id']}"):
                            delete_image(prompt_data["id"], prompt_data["filename"])
                            st.experimental_rerun()

    with tab3:
        st.header("Prompt History")
        prompts = get_all_prompts()
        if not prompts:
            st.info("No prompts submitted yet. Create your first image in the 'Generate Images' tab!")
        else:
            for i, prompt_data in enumerate(prompts):
                with st.expander(f"Prompt {i+1}: {prompt_data['prompt'][:50]}..." if len(prompt_data['prompt']) > 50 else prompt_data['prompt']):
                    col1, col2 = st.columns([1, 2])
                    with col1:
                        img_b64 = get_image_base64(prompt_data["filename"])
                        if img_b64:
                            st.image(prompt_data["filename"], use_container_width=True)
                            with open(prompt_data["filename"], "rb") as file:
                                st.download_button(
                                    label="Download Image",
                                    data=file,
                                    file_name=prompt_data["filename"].split("/")[-1],
                                    mime="image/png",
                                    key=f"download_history_{prompt_data['id']}"
                                )
                            if st.button("Delete", key=f"delete_history_{prompt_data['id']}"):
                                delete_image(prompt_data["id"], prompt_data["filename"])
                                st.experimental_rerun()
                    with col2:
                        st.write(f"**Full Prompt:** {prompt_data['prompt']}")
                        st.write(f"**Expected Style:** {prompt_data['expected_style']}")
                        st.write(f"**Created:** {prompt_data['created_at']}")
                        if prompt_data["score"]:
                            st.write(f"**Score:** {prompt_data['score']}/10")
                            st.write(f"**Feedback:** {prompt_data['feedback'] if prompt_data['feedback'] else 'None'}")
                        else:
                            st.write("Not yet evaluated")

    with tab4:
        st.header("Evaluation Report")
        prompts = get_all_prompts()
        evaluated_prompts = [p for p in prompts if p["score"] is not None]
        if not evaluated_prompts:
            st.info("No evaluations yet. Rate some generated images to see your evaluation report.")
        else:
            st.subheader("Overall Statistics")
            avg_score = sum(p["score"] for p in evaluated_prompts) / len(evaluated_prompts)
            st.metric("Average Match Score", f"{avg_score:.1f}/10")

            st.subheader("Performance by Style")
            styles = {}
            for p in evaluated_prompts:
                style = p["expected_style"]
                if style not in styles:
                    styles[style] = []
                styles[style].append(p["score"])
            for style, scores in styles.items():
                avg = sum(scores) / len(scores)
                st.metric(f"{style.capitalize()} Style", f"{avg:.1f}/10")

            st.subheader("Detailed Evaluations")
            for p in evaluated_prompts:
                with st.expander(f"{p['prompt'][:50]}..." if len(p['prompt']) > 50 else p['prompt']):
                    col1, col2 = st.columns([1, 2])
                    with col1:
                        img_b64 = get_image_base64(p["filename"])
                        if img_b64:
                            st.image(p["filename"], use_container_width=True)
                    with col2:
                        st.write(f"**Prompt:** {p['prompt']}")
                        st.write(f"**Expected Style:** {p['expected_style']}")
                        st.write(f"**Score:** {p['score']}/10")
                        st.write(f"**Feedback:** {p['feedback'] if p['feedback'] else 'None'}")

# Load sample data
def load_sample_data():
    with sqlite3.connect('image_generator.db') as conn:
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM prompts")
        count = c.fetchone()[0]
    if count == 0:
        sample_data = [
            {"prompt": "a fantasy castle in the clouds", "expected_style": "realistic"},
            {"prompt": "a futuristic robot chef in a kitchen", "expected_style": "cyberpunk"},
            {"prompt": "a panda riding a bicycle in space", "expected_style": "cartoon"}
        ]
        st.session_state.demo_mode = True
        for item in sample_data:
            image = generate_image(item["prompt"], item["expected_style"])
            filename, prompt_id = save_image(image, item["prompt"], item["expected_style"])
            if prompt_id:
                score = random.randint(6, 9)
                feedback_options = [
                    "Great image, matches my expectation",
                    "Nice style, but could use more detail",
                    "Colors are perfect, composition is good"
                ]
                feedback = random.choice(feedback_options)
                update_evaluation(prompt_id, score, feedback)

# Run the app
if __name__ == "__main__":
    load_sample_data()
    main()