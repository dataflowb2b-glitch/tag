# 📦 CBR Logística — Portal de Recebimento

Portal completo de emissão de etiquetas de recebimento com integração Supabase.

---

## 🚀 Deploy no Streamlit Cloud (passo a passo)

### 1. Suba o projeto para o GitHub

```bash
git init
git add app.py requirements.txt .gitignore
# ⚠️  NÃO adicione .streamlit/secrets.toml
git commit -m "CBR Logística - Portal de Recebimento"
git remote add origin https://github.com/SEU_USUARIO/cbr-logistica.git
git push -u origin main
```

### 2. Acesse o Streamlit Cloud

Acesse → [share.streamlit.io](https://share.streamlit.io)

- Clique em **New app**
- Selecione seu repositório e o arquivo `app.py`
- Clique em **Advanced settings → Secrets**

### 3. Cole as credenciais em Secrets

No campo **Secrets** do Streamlit Cloud, cole exatamente:

```toml
SUPABASE_URL = "https://qoohwyaajiapqyjvotms.supabase.co"
SUPABASE_KEY = "sb_publishable_SD5nlCcBenrdnftETZZ7JQ_3QlLizf_"
OPERADOR     = "CBR LOGÍSTICA"
```

### 4. Deploy!

Clique em **Deploy** — em ~1 minuto o portal estará online com URL pública.

---

## 💻 Rodar localmente

```bash
pip install -r requirements.txt
streamlit run app.py
```

Crie o arquivo `.streamlit/secrets.toml` com as credenciais (veja o modelo incluído).

---

## 📁 Estrutura do projeto

```
cbr-logistica/
├── app.py                        ← App Streamlit principal
├── requirements.txt              ← Dependências Python
├── .gitignore                    ← Ignora secrets e arquivos locais
├── README.md                     ← Este arquivo
├── .streamlit/
│   └── secrets.toml              ← ⚠️ NÃO subir no GitHub
│
│   (opcional — emissor desktop)
├── emissor_etiqueta_cbr.py       ← Emissor Tkinter local
└── portal_cbr.html               ← Portal HTML offline
```

---

## ✅ Funcionalidades

| Página | O que faz |
|---|---|
| 📊 Dashboard | Totais, gráficos e últimos recebimentos |
| 📋 Recebimentos | Tabela completa, busca, detalhe, CSV |
| 📄 Importar XML | Upload NF-e, extração automática |
| ✏️ Inserir Manual | Formulário com todos os campos |
| 🖨️ Emitir Etiquetas | Navegação 1/N…N/N, baixar PNG e ZIP |

---

## 🗄️ Banco de dados

Execute o `setup_supabase.sql` no **SQL Editor** do seu projeto Supabase antes de usar.
