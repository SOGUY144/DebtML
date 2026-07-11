# DTI ML — Dashboard วิเคราะห์ความเสี่ยงหนี้ครัวเรือนเชิงนโยบาย

ระบบ Machine Learning สำหรับพยากรณ์ความเสี่ยงภาวะหนี้สินครัวเรือน (Debt-to-Income Ratio) ใน **ระดับจังหวัดของประเทศไทย** พัฒนาในรูปแบบ Leading Indicator เพื่อช่วยให้ผู้กำหนดนโยบายเห็นสัญญาณเตือนจังหวัดกลุ่มเสี่ยงล่วงหน้า ก่อนที่ผลสำรวจรอบถัดไปจะยืนยันสถานการณ์จริง

**ตัวอย่างใช้งานจริง:** [debt-ml.vercel.app](https://debt-ml.vercel.app)

---

## ระบบทำอะไรได้บ้าง

ใช้ข้อมูลสำรวจหนี้สินและรายได้ครัวเรือนย้อนหลังจากสำนักงานสถิติแห่งชาติ (NSO) โดยระบบจะ:

1. สร้าง **Lag Feature และ Growth Feature** (ค่า DTI, หนี้สิน, รายได้ของรอบก่อนหน้า และอัตราการเติบโตรายปี)
2. เทรนแบบจำลอง Classification 3 ตัว ได้แก่ **Logistic Regression, Random Forest, LightGBM** เพื่อพยากรณ์ว่าจังหวัดจะอยู่ในสถานะ `Stable` หรือ `High-Risk` (DTI > 1.0)
3. แสดงผลการพยากรณ์ ผลประเมินแบบจำลอง และเครื่องมือจำลองนโยบาย (What-If Simulation) ผ่านหน้าเว็บ dashboard

> **หมายเหตุเรื่องตัวแปรตาม (Label):** ตัวแปรตามที่ใช้เป็น **Proxy Label** คือเกณฑ์ DTI ที่เกินค่าที่กำหนด ไม่ใช่สถานะการผิดนัดชำระหนี้จริง (NPL) เนื่องจากข้อมูล NSO เป็นข้อมูลเฉลี่ยระดับจังหวัด (Aggregate-level) และไม่มีข้อมูลการผิดนัดชำระหนี้รายครัวเรือน ผลการประเมินแบบจำลองจึงสะท้อนความสามารถในการจำแนกกลุ่มตามเกณฑ์ DTI เท่านั้น ไม่ใช่ความสามารถในการพยากรณ์การผิดนัดชำระหนี้จริง

---

## เทคโนโลยีที่ใช้

| ส่วน | เทคโนโลยี |
|---|---|
| ML / Backend | Python, scikit-learn, LightGBM, pandas, FastAPI |
| Frontend | Next.js (React), Plotly |
| Deployment | Vercel (frontend), backend แยก host ต่างหาก (ดู `NEXT_PUBLIC_API_URL`) |

---

## โครงสร้างโปรเจกต์

```
DebtML/
├── backend/
│   ├── main.py          # FastAPI app — รวม API endpoints ทั้งหมด
│   └── ml_core.py        # โหลดข้อมูล, สร้างฟีเจอร์, เทรนโมเดล
├── frontend/
│   └── src/app/           # หน้าเว็บ Next.js: Overview, Deep-Dive, Models, Simulate
├── *.xlsx                 # ข้อมูลสำรวจ NSO ดิบ (หนี้สินและรายได้ แยกตามจังหวัด/ปี)
├── requirements.txt        # Dependency ฝั่ง backend
└── DTI_ML.ipynb / DebtML.ipynb  # Notebook สำหรับสำรวจข้อมูลระหว่างพัฒนาโมเดล
```

---

## หน้าต่าง ๆ ใน Dashboard

| หน้า | รายละเอียด |
|---|---|
| **Overview** | ภาพรวมระดับประเทศ — จำนวนจังหวัดทั้งหมด, จำนวนจังหวัดกลุ่มเสี่ยง, DTI เฉลี่ย, Top 10 จังหวัดที่มีภาระหนี้สูงสุด |
| **Deep-Dive** | แนวโน้มย้อนหลังรายจังหวัด แสดงหนี้สิน รายได้ และ DTI (ปี 2547–2566) |
| **Models** | เปรียบเทียบผลลัพธ์แบบจำลอง (PR-AUC, Confusion Matrix, Precision-Recall Curve) และ Feature Importance ของทั้ง 3 โมเดล |
| **Simulate** | เครื่องมือจำลองนโยบาย (What-If) — ปรับอัตราการเติบโตของหนี้สิน/รายได้ที่คาดการณ์ แล้วดูผลพยากรณ์จากทั้ง 3 โมเดลแบบ real-time |

---

## วิธีรันใช้งานในเครื่อง

**Backend**
```bash
pip install -r requirements.txt
cd backend
python main.py
# → รันที่ http://localhost:8000
```

**Frontend**
```bash
cd frontend
npm install
npm run dev
# → รันที่ http://localhost:3000
```

ตั้งค่า `NEXT_PUBLIC_API_URL` ในฝั่ง frontend ให้ชี้ไปยัง backend หากไม่ได้รันที่ `localhost:8000`

---

## ข้อจำกัดที่ทราบอยู่แล้ว

- **Class Imbalance**: จังหวัดกลุ่มเสี่ยงสูงมีจำนวนน้อยมากในชุดข้อมูล ทำให้แบบจำลองกลุ่ม Tree-based (Random Forest, LightGBM) ยังมีค่า Recall ต่ำกว่า Logistic Regression ในปัจจุบัน — ดูตัวเลขทั้งหมดได้ที่หน้า Models
- **ข้อมูลระดับ Aggregate**: การพยากรณ์ทำในระดับจังหวัด ไม่ใช่ระดับครัวเรือนรายคน เนื่องจากข้อจำกัดของข้อมูลที่มีจาก NSO

---

## แหล่งที่มาของข้อมูล

ข้อมูลสำรวจหนี้สินและรายได้ครัวเรือน สำนักงานสถิติแห่งชาติ (National Statistical Office of Thailand)
