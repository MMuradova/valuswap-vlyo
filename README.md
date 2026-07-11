# 🌿 ValuSwap-VLYO — Dəyərə Əsaslanan Barter Platforması

ValuSwap-VLYO istifadəçilərin öz məhsullarını pul ödəmədən, yalnız dəyər əsasında dəyişdirə biləcəyi AI-powered barter platformasıdır.

## 🚀 Necə işləyir?

1. İstifadəçi Gradio interfeysindən məhsul şəklini yükləyir
2. **Claude Vision API** şəkli analiz edir — ad, kateqoriya, vəziyyət və AZN qiymətini avtomatik təyin edir
3. Məlumat **FastAPI** backend-ə göndərilir və **PostgreSQL**-də saxlanılır
4. `/match` endpoint-i bənzər dəyərli məhsulları tapır (nəticələr **Redis**-də keşlənir)
5. İstifadəçi dəyişmə təklifi yaradır — sistem qiymət fərqini avtomatik hesablayır
6. **n8n + Telegram** inteqrasiyası ilə bildirişlər göndərilir

## 🛠️ Texnologiyalar

| Texnologiya | Rolu |
|---|---|
| Python (OOP) | `User`, `Product` (baza) → `Electronics`/`Clothing` (alt-class), `Trade` state machine |
| FastAPI + Pydantic | Validasiyalı REST API (`/products`, `/match`, `/trade-offer`) |
| PostgreSQL + SQLAlchemy | Məhsul, istifadəçi və dəyişmə təkliflərinin daimi saxlanması |
| Redis | Uyğunluq nəticələrinin keşlənməsi (60 saniyə TTL) |
| Claude Vision API | Məhsul şəklindən avtomatik ad/kateqoriya/qiymət təyini |
| Gradio | İstifadəçi interfeysi |
| n8n + Telegram Bot API | Workflow automasiyası və bildirişlər |

## 📦 Layihə Strukturu