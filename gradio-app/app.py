"""
ValuSwap-VLYO — Gradio UI (FastAPI backend-ə qoşulmuş versiya)

İstifadəçi məhsul şəkli yükləyir → Claude Vision AZN qiyməti/kateqoriya təyin edir →
FastAPI backend-ə (/products) göndərilir → PostgreSQL-də saxlanılır →
/match endpoint-i ilə uyğun barter təklifləri göstərilir.

İşə salmaq:
    pip install gradio anthropic requests python-dotenv
    python app.py
"""
import os
import json
import base64
import requests
import gradio as gr
from dotenv import load_dotenv
import anthropic

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
# FastAPI backend-in ünvanı. Lokal işlədəndə dəyişməyə ehtiyac yoxdur.
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None


# --------------------------------------------------------------------------
# Claude Vision ilə şəkil analizi
# --------------------------------------------------------------------------
def analyze_image(image_path):
    if not image_path:
        return None, "Zəhmət olmasa əvvəlcə bir şəkil yükləyin."
    if client is None:
        return None, "ANTHROPIC_API_KEY tapılmadı. .env faylını yoxlayın."

    with open(image_path, "rb") as f:
        image_data = base64.standard_b64encode(f.read()).decode("utf-8")

    media_type = "image/jpeg"
    if image_path.lower().endswith(".png"):
        media_type = "image/png"

    try:
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=500,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_data,
                        },
                    },
                    {
                        "type": "text",
                        "text": (
                            "Bu şəkildəki məhsulu analiz et. Yalnız JSON formatında, "
                            "başqa heç bir mətn olmadan bu sahələrlə cavab ver: "
                            '{"name": "...", "category": "...", "condition": "Yeni/Az istifadə olunmuş/İstifadə olunmuş", "price_azn": rəqəm}. '
                            "Qiyməti Azərbaycan bazarına uyğun təxmini AZN olaraq ver."
                        ),
                    },
                ],
            }],
        )
        raw = message.content[0].text
        clean = raw.replace("```json", "").replace("```", "").strip()
        data = json.loads(clean)
        return data, "✅ Analiz tamamlandı — məlumatları yoxlayıb təsdiqləyin."
    except Exception as e:
        return None, f"❌ Xəta: {e}"


def on_analyze(image_path):
    data, status = analyze_image(image_path)
    if data is None:
        return status, "", "", "Yeni", 0
    return (
        status,
        data.get("name", ""),
        data.get("category", ""),
        data.get("condition", "Yeni"),
        float(data.get("price_azn", 0)),
    )


# --------------------------------------------------------------------------
# Backend-ə göndərmək
# --------------------------------------------------------------------------
def submit_product(telegram_id, name, category, condition, price_azn):
    if not telegram_id or not name or not category:
        return "⚠️ Zəhmət olmasa bütün sahələri doldurun (İstifadəçi ID, Ad, Kateqoriya).", "", None

    payload = {
        "owner_telegram_id": str(telegram_id),
        "name": name,
        "category": category,
        "condition": condition,
        "price_azn": float(price_azn),
        "type": "electronics" if "elektro" in category.lower() or "electronic" in category.lower() else "product",
    }

    try:
        resp = requests.post(f"{BACKEND_URL}/products", json=payload, timeout=10)
        resp.raise_for_status()
        product = resp.json()
    except Exception as e:
        return f"❌ Backend-ə qoşulma xətası: {e}", "", None

    product_id = product["id"]

    # Uyğun təklifləri soruş
    match_text = "Uyğun təklif tapılmadı."
    try:
        match_resp = requests.get(f"{BACKEND_URL}/match/{product_id}", params={"limit": 3}, timeout=10)
        if match_resp.ok:
            matches = match_resp.json()
            if matches:
                lines = [
                    f"• {m['name']} — {m['price_azn']} AZN (bənzərlik: {round(m['similarity_score']*100)}%, ID: {m['product_id']})"
                    for m in matches
                ]
                match_text = "\n".join(lines)
    except Exception:
        pass

    success_msg = f"✅ Məhsul əlavə olundu! ID: {product_id} — {product['name']} ({product['price_azn']} AZN)"
    return success_msg, match_text, product_id


def list_products(category_filter):
    try:
        params = {"category": category_filter} if category_filter else {}
        resp = requests.get(f"{BACKEND_URL}/products", params=params, timeout=10)
        resp.raise_for_status()
        products = resp.json()
    except Exception as e:
        return f"Backend-ə qoşulma xətası: {e}"

    if not products:
        return "Hələ heç bir məhsul yoxdur."

    rows = [
        f"#{p['id']} — {p['name']} | {p['category']} | {p['condition']} | {p['price_azn']} AZN"
        for p in products
    ]
    return "\n".join(rows)


def create_trade_offer(proposer_id, target_id):
    if not proposer_id or not target_id:
        return "⚠️ Hər iki məhsul ID-sini daxil edin."
    try:
        resp = requests.post(
            f"{BACKEND_URL}/trade-offer",
            json={"proposer_product_id": int(proposer_id), "target_product_id": int(target_id)},
            timeout=10,
        )
        resp.raise_for_status()
        trade = resp.json()
        return f"✅ Təklif yaradıldı! Trade ID: {trade['id']} — Status: {trade['status']} — Qiymət fərqi: {trade['price_diff_azn']} AZN"
    except Exception as e:
        return f"❌ Xəta: {e}"


# --------------------------------------------------------------------------
# Gradio UI
# --------------------------------------------------------------------------
NATURE_CSS = """
.gradio-container { background-color: #e8f5e2 !important; }
.gr-panel { background-color: #fef9ec !important; }
h1, h2, h3 { color: #3d2b1f !important; }
"""

with gr.Blocks(css=NATURE_CSS, title="ValuSwap-VLYO") as demo:
    gr.Markdown("# 🌿 ValuSwap-VLYO — Dəyərə Əsaslanan Barter Platforması")
    gr.Markdown("Şəklini yüklə, AI qiymətini təyin etsin, uyğun dəyişmə təklifini tap!")

    with gr.Tab("📸 Şəkildən AI Analiz"):
        with gr.Row():
            with gr.Column():
                image_input = gr.Image(type="filepath", label="Məhsul şəkli")
                analyze_btn = gr.Button("🔍 Təhlil Et", variant="primary")
                analyze_status = gr.Textbox(label="Status", interactive=False)

            with gr.Column():
                telegram_id_input = gr.Textbox(label="Telegram İstifadəçi ID", placeholder="123456789")
                name_input = gr.Textbox(label="Məhsul Adı")
                category_input = gr.Textbox(label="Kateqoriya")
                condition_input = gr.Dropdown(
                    ["Yeni", "Az istifadə olunmuş", "İstifadə olunmuş"],
                    label="Vəziyyət", value="Yeni",
                )
                price_input = gr.Number(label="Qiymət (AZN)")
                submit_btn = gr.Button("✅ Məhsulu Əlavə Et", variant="primary")

        submit_status = gr.Textbox(label="Nəticə", interactive=False)
        match_output = gr.Textbox(label="🔄 Uyğun Təkliflər", interactive=False, lines=4)
        new_product_id = gr.Number(label="Yaradılan Məhsul ID-si", interactive=False)

        analyze_btn.click(
            on_analyze, inputs=[image_input],
            outputs=[analyze_status, name_input, category_input, condition_input, price_input],
        )
        submit_btn.click(
            submit_product,
            inputs=[telegram_id_input, name_input, category_input, condition_input, price_input],
            outputs=[submit_status, match_output, new_product_id],
        )

    with gr.Tab("📋 Bütün Məhsullar"):
        category_filter_input = gr.Textbox(label="Kateqoriyaya görə filtrlə (boş = hamısı)")
        refresh_btn = gr.Button("🔄 Yenilə")
        products_list = gr.Textbox(label="Məhsullar", interactive=False, lines=15)
        refresh_btn.click(list_products, inputs=[category_filter_input], outputs=[products_list])

    with gr.Tab("🔄 Dəyişmə Təklifi"):
        gr.Markdown("İki məhsul ID-si daxil edərək dəyişmə təklifi yarat.")
        proposer_input = gr.Number(label="Sizin məhsulunuzun ID-si")
        target_input = gr.Number(label="İstədiyiniz məhsulun ID-si")
        trade_btn = gr.Button("🤝 Təklif Yarat", variant="primary")
        trade_result = gr.Textbox(label="Nəticə", interactive=False)
        trade_btn.click(create_trade_offer, inputs=[proposer_input, target_input], outputs=[trade_result])

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)