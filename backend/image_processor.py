import torch
import open_clip
import pytesseract
from PIL import Image

device = "cuda" if torch.cuda.is_available() else "cpu"

model, _, preprocess = open_clip.create_model_and_transforms(
    "ViT-B-32", pretrained="openai"
)
tokenizer = open_clip.get_tokenizer("ViT-B-32")

model.to(device)
model.eval()

# CLIP's own learned temperature — used to convert raw cosine similarities
# into calibrated confidence scores via softmax (same technique CLIP uses
# for zero-shot classification).
def get_logit_scale():
    return model.logit_scale.exp().item()


def embed_image(image_path):
    """
    Convert an image file into a CLIP embedding vector.
    """
    image = Image.open(image_path).convert("RGB")
    image_input = preprocess(image).unsqueeze(0).to(device)

    with torch.no_grad():
        embedding = model.encode_image(image_input)
        embedding /= embedding.norm(dim=-1, keepdim=True)

    return embedding.cpu().numpy()[0]


def embed_text_query(text, use_template=True):
    """
    Convert a text query into the SAME embedding space as images,
    so a text question can search against stored images.

    use_template wraps the raw query into a CLIP-style caption prompt
    ("a photo of X") — CLIP was trained on image-caption pairs, so a
    caption-shaped query embeds much more meaningfully than a raw
    question fragment like "give me human image".
    """
    if use_template:
        text = f"a photo of {text}"

    tokens = tokenizer([text]).to(device)

    with torch.no_grad():
        embedding = model.encode_text(tokens)
        embedding /= embedding.norm(dim=-1, keepdim=True)

    return embedding.cpu().numpy()[0]


def extract_text_from_image(image_path):
    """
    OCR on an image file — pulls out any embedded text (certificates,
    scanned documents, screenshots with text, IDs, etc.). Returns an
    empty string if the image has no readable text or OCR fails.
    """
    try:
        image = Image.open(image_path).convert("RGB")
        text = pytesseract.image_to_string(image)
        return text.strip()
    except Exception:
        return ""


def process_image(image_path):
    """
    Combined helper: returns both the CLIP embedding (for visual/semantic
    similarity search) and any OCR'd text (for exact keyword search on
    certificates/documents shown as images) in one call.
    """
    return {
        "embedding": embed_image(image_path),
        "ocr_text": extract_text_from_image(image_path),
    }