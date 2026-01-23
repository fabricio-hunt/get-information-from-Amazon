
# 🛒 Amazon Product Scraper Pro v2.0

<div align="center">

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-1.51.0-FF4B4B.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![Status](https://img.shields.io/badge/Status-Active-success.svg)

**Extract complete product data from Amazon with automatic AI translation to Portuguese (PT-BR)** 🇧🇷

[Demo](#-demo) • [Features](#-features) • [Installation](#-installation) • [Usage](#-usage) • [Deploy](#-deploy)

</div>

---

## 📖 About the Project

**Amazon Product Scraper Pro v2.0** is a Streamlit web app built with Python that lets you extract detailed product data from Amazon and automatically translate it into Brazilian Portuguese using **Deep Translator** or **Gemini AI**.

### 🎯 Why use this tool?

* ✅ **Easy to use** – No coding required
* ✅ **AI Translation** – Automatic translation to PT-BR (Deep Translator or Gemini AI)
* ✅ **Complete product data** – Title, price, rating, brand, specs, and more
* ✅ **Export ready** – CSV, JSON, Excel, and VTEX markdown
* ✅ **Free & open source**

---

## ✨ Features

### 📊 Extracted Data

| Field                   | Description                              |
| ----------------------- | ---------------------------------------- |
| **Title**               | Product name                             |
| **Price**               | Current product price                    |
| **Rating**              | Average star rating                      |
| **Number of Reviews**   | Total number of reviews                  |
| **Availability**        | In stock / Out of stock                  |
| **Brand**               | Product manufacturer                     |
| **ASIN**                | Amazon unique code                       |
| **Image**               | Main product image URL                   |
| **About This Item**     | Key features and highlights              |
| **Product Information** | Dimensions, weight, model, battery, etc. |
| **Technical Details**   | Extra product specs and info             |

---

### 🤖 AI Translation Options

* **Deep Translator (default)** – Fast and simple
* **Gemini AI (optional)** – Higher-quality, context-aware translations
* Smart handling for long texts (auto-split and merge)
* Preserves links, numbers, and codes
* Built-in progress bar for translation

---

### 📏 Advanced Measurement Conversion (New)

Automatically converts US imperial units to Brazilian metric standards with high precision:

* **Weight:** `lbs`, `oz` → `kg`, `g` (e.g., "5.5 lbs" → "2,49 kg")
* **Length:** `inches`, `ft`, `yards` → `cm`, `m` (e.g., "10 inches" → "25,4 cm")
* **Volume:** `gal`, `fl oz`, `cups` → `L`, `ml` (e.g., "1 gallon" → "3,79 L")
* **Temperature:** `°F` → `°C` (e.g., "98.6°F" → "37,0°C")
* **Area/Energy:** `sq ft` → `m²`, `BTU` → `J/kW`

### 👕 Smart Clothing Size Guide (New)

Context-aware conversion for apparel based on gender and product type:

* **Men's:** US sizes (XS-XXL) → BR sizes (PP-XXG) and Shoe sizes (US 10 → BR 42)
* **Women's:** Dress sizes (US 4 → BR 38) and Shoe sizes (US 7 → BR 37)
* **Children/Infant:** Age-based conversion (e.g., 2T → 2 anos)
* **Smart Detection:** Automatically detects gender from product title/description to apply the correct size chart.

---

### 🏪 VTEX Export (New)

Easily export your scraped and translated product data in **VTEX-compatible markdown format**.

Example:

```markdown
#### KEEPONFIT Smart Watch
<endDescription>
Brand: KEEPONFIT<br>
ASIN: B0DDQ7YCK6<br>
Color: Rose Gold<br>
Battery: 7 days<br>
Disclaimer: Images are for illustration purposes only
```

---

## 🚀 Installation

### Requirements

* Python 3.8+
* pip (Python package manager)

### Step 1 – Clone the Repository

```bash
git clone https://github.com/your-username/amazon-scraper-pro.git
cd amazon-scraper-pro
```

### Step 2 – Install Dependencies

```bash
pip install -r requirements.txt
```

**requirements.txt**

```txt
streamlit
beautifulsoup4
requests
pandas
openpyxl
deep-translator
google-generativeai
```

### Step 3 – Run the App

```bash
streamlit run app.py
```

The app will open automatically in your browser at:
`http://localhost:8501`

---

## 💡 Usage

### 1️⃣ Paste an Amazon Product URL

Example:

```
https://www.amazon.com/dp/B08N5WRWNW
```

### 2️⃣ Click “🚀 Collect Data”

Wait a few seconds while the scraper gathers product info.

### 3️⃣ Optional: Enable Translation

In the sidebar:

* ✅ Enable PT-BR translation (default)
* 🤖 Use Gemini AI for better translation quality (requires API key)

### 4️⃣ Export Data

Choose the format you prefer:

* 📄 CSV
* 📋 JSON
* 📊 Excel
* 🏪 VTEX Markdown

---

## ⚙️ Settings

* 🧠 **Gemini AI Integration** – Optional, requires a free API key from [MakerSuite](https://makersuite.google.com/app/apikey)
* 🛡️ **Anti-blocking system** – Random headers and delays to reduce Amazon blocking
* 🔒 **VPN Tip:** Use the **Opera Browser** (built-in free VPN)

---

## 🌍 Deploy Options

### Streamlit Cloud (Free)

1. Push your project to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub account and select your repo
4. Deploy 🚀

Your app will be live at:

```
https://your-username-amazon-scraper.streamlit.app
```

Other deploy options:

* **Render**
* **Railway**
* **Heroku**

---

## 🛠️ Technologies Used

| Tech                | Purpose              |
| ------------------- | -------------------- |
| **Python 3.8+**     | Main language        |
| **Streamlit**       | Web interface        |
| **BeautifulSoup4**  | Web scraping         |
| **Requests**        | HTTP requests        |
| **Pandas**          | Data processing      |
| **Deep Translator** | AI translation       |
| **Google Gemini**   | Advanced translation |
| **OpenPyXL**        | Excel export         |

---

## 📂 Project Structure

```
amazon-scraper-pro/
│
├── app.py                 # Main Streamlit app
├── requirements.txt       # Dependencies
├── README.md              # Documentation
└── .gitignore
```

---

## ⚠️ Important Notes

### Responsible Use

* ⚖️ Respect Amazon’s Terms of Service
* 🚫 Avoid mass scraping
* 🧩 Use for educational or testing purposes only

### Limitations

* 🔒 Amazon may block repeated requests
* 🧱 Layout changes can break selectors
* 🌐 Some products have different page structures
* 🕒 Translation may take longer for long descriptions

---

## 🐛 Troubleshooting

| Issue                               | Solution                                    |
| ----------------------------------- | ------------------------------------------- |
| **"Deep Translator not installed"** | `pip install deep-translator`               |
| **"Amazon blocked the request"**    | Use a VPN or wait a few minutes             |
| **"N/A" data fields**               | Try another product URL (layout may differ) |

---

## 🤝 Contributing

Contributions are welcome! 🎉

1. Fork the project
2. Create a feature branch
3. Commit your changes
4. Push and open a Pull Request

---

## 🧭 Roadmap

* [ ] Multi-URL support
* [ ] Price comparison
* [ ] Price history tracking
* [ ] Price drop alerts
* [ ] REST API
* [ ] Dashboard with charts
* [ ] Support for other marketplaces (Mercado Livre, etc.)

---

## 📄 License

This project is under the MIT License. See the [LICENSE](LICENSE) file for details.

---

## 👤 Author

**Fabricio Baraúna**

* GitHub: [@fabriciobarauna](https://github.com/fabriciobarauna)
* LinkedIn: [Fabricio Baraúna](https://linkedin.com/in/fabriciobarauna)
* Email: [fabriciomacedo@bemol.com.br](mailto:fabriciomacedo@bemol.com.br)

---

## 🌟 Support the Project

If this tool helped you, please consider giving it a ⭐️ on GitHub!

---

## 🏆 Credits

* [Streamlit](https://streamlit.io/) – Web framework
* [Beautiful Soup](https://www.crummy.com/software/BeautifulSoup/) – HTML parsing
* [Deep Translator](https://github.com/nidhaloff/deep-translator) – Translation
* [Google Gemini AI](https://deepmind.google/) – Advanced language model
* Python Community 🐍

---

**Last update:** November 2025

---


