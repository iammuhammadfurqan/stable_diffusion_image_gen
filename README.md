# Text-to-Image App

A Streamlit web application for generating images from text prompts using Stable Diffusion via the Hugging Face API. Users can select different styles, view a gallery of generated images, rate generations, and review prompt history and evaluation reports.

---

## Features

- **Text-to-Image Generation:** Enter a prompt and generate an image using Stable Diffusion.
- **Style Selection:** Choose from "realistic", "cyberpunk", or "cartoon" styles (styles are applied via prompt engineering).
- **Image Gallery:** Browse, download, and delete previously generated images.
- **Prompt History:** Review all prompts and their generated images.
- **Evaluation:** Rate images and provide feedback; view evaluation statistics.
- **Rate Limiting:** Prevents excessive API usage.
- **Local Database:** Stores prompts, images, scores, and feedback.
- **Demo Mode:** Returns a placeholder image if the API token is missing.

---

## Setup

### 1. Clone the Repository

```sh
git clone https://github.com/iammuhammadfurqan/stable_diffusion_image_gen.git
cd text-to-image-app
```

### 2. Install Dependencies

```sh
pip install -r requirements.txt
```

### 3. Configure Secrets

Create a `.streamlit/secrets.toml` file and add your Hugging Face API token:

```toml
HUGGING_FACE_API_TOKEN = "your_huggingface_api_token"
```

### 4. Run the App

```sh
streamlit run app.py
```

---

## Usage

1. Enter a descriptive prompt in the "Generate Images" tab.
2. Select a style.
3. Click "Generate Image" to create and view your image.
4. Browse, download, or delete images in the "Image Gallery".
5. Rate images and provide feedback.
6. View prompt history and evaluation reports in their respective tabs.

---

## File Structure

- `app.py` — Main Streamlit application.
- `generated_images/` — Folder for storing generated images (auto-created).
- `image_generator.db` — SQLite database for prompts and metadata.
- `.streamlit/secrets.toml` — Store your Hugging Face API token here.
- `.gitignore` — Ensures sensitive and generated files are not tracked.

---

## Notes

- The app uses the `stabilityai/stable-diffusion-xl-base-1.0` model for all styles, modifying the prompt for style effects.
- If the API token is missing or invalid, the app runs in demo mode with placeholder images.
- All generated images and prompt data are stored locally.

---

## License

This project is licensed under the MIT License.

---

## Acknowledgments

- [Streamlit](https://streamlit.io/)
- [Hugging Face](https://huggingface.co/)
- [Stable Diffusion](https://stability.ai/)

---