import streamlit as st
import pandas as pd
import io
import re
import os
from datetime import datetime

# === KONFIGURACJA STRONY ===
st.set_page_config(page_title="Panel administratora: zwolnienia lekarskie", layout="wide")

# === TRYB I MOTYW ===
theme = st.sidebar.radio("Motyw:", ("Jasny", "Ciemny"))
if theme == "Ciemny":
    base_bg = '#1f2937'; fg = '#f3f4f6'; card_bg = '#273242'
else:
    base_bg = '#f5f5f5'; fg = '#1f2937'; card_bg = '#ffffff'

# === GLOBALNY STYLING ===
st.markdown(f"""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;700&display=swap');
  html, body {{background-color: {base_bg}; color: {fg}; font-family: 'Roboto', sans-serif; margin: 0; padding: 0;}}
  .stApp > div:first-child {{padding: 1rem 2rem;}}
  h1, .stHeader {{font-weight: 700; margin-bottom: 1rem;}}
  .stTextInput>div>div>input, .stTextArea>div>textarea {{background: {card_bg}; border: none; border-radius: 12px; padding: 12px; box-shadow: 2px 2px 5px rgba(0,0,0,0.1), -2px -2px 5px rgba(255,255,255,0.7); transition: box-shadow 0.3s ease;}}
  .stTextInput>div>div>input:focus, .stTextArea>div>textarea:focus {{outline: none; box-shadow: inset 2px 2px 5px rgba(0,0,0,0.2), inset -2px -2px 5px rgba(255,255,255,0.5);}}
  .stButton>button {{background: linear-gradient(145deg, {card_bg}, #e0e0e0); color: {fg}; border-radius: 20px; padding: 0.8em 2em; box-shadow: 4px 4px 6px rgba(0,0,0,0.2), -4px -4px 6px rgba(255,255,255,0.5); transition: all 0.2s ease; font-weight: 500;}}
  .stButton>button:hover {{transform: translateY(-2px); box-shadow: 6px 6px 8px rgba(0,0,0,0.25), -6px -6px 8px rgba(255,255,255,0.6);}}
  .pagination {{display: flex; justify-content: center; align-items: center; gap: 1rem; margin: 2rem 0;}}
  @media only screen and (max-width: 768px) {{.stApp > div:first-child {{padding: 1rem;}} .stTextInput>div>div>input, .stTextArea>div>textarea {{padding: 8px;}} .stButton>button {{padding: 0.6em 1.2em; font-size: 0.9rem;}}}}
</style>
""", unsafe_allow_html=True)

# === LOGOWANIE ADMINISTRATORA ===
with st.sidebar:
    st.title("🔒 Panel Administratora")
    haslo = st.text_input("Hasło:", type="password")
    if 'zalogowany' not in st.session_state:
        st.session_state.zalogowany = False
    if st.button("Zaloguj się"):
        if haslo == "A9r#Pz8!mX3v@Lt6":
            st.session_state.zalogowany = True
            st.success("Pomyślnie zalogowano!")
        else:
            st.error("Nieprawidłowe hasło")

if not st.session_state.get('zalogowany'):
    st.title("Witaj w Systemie")
    st.info("Zaloguj się, aby kontynuować.")
    st.stop()

# === NAGŁÓWEK PANELU ===
st.header("📄 Wyszukiwanie Zwolnień Lekarskich")

# === DANE WEJŚCIOWE ===
plik_excel = st.file_uploader("Prześlij plik PSZL.xlsx", type="xlsx")
pesel_input = st.text_area("Wprowadź numery PESEL (po jednym w wierszu):", height=100)

# === WALIDACJA PESEL ===
def waliduj_pesel(p):
    if not re.fullmatch(r"\d{11}", p): return False
    wagi = [1,3,7,9,1,3,7,9,1,3]; cyfry = list(map(int, p))
    s = sum(w*d for w,d in zip(wagi, cyfry)); return (10 - s % 10) % 10 == cyfry[-1]

# === ŁADOWANIE EXCEL ===
@st.cache_data
def zaladuj_excel(dane): return pd.read_excel(io.BytesIO(dane), sheet_name=None, header=None)

# === AKCJA WYSZUKIWANIA ===
if st.button("🔍 Rozpocznij Wyszukiwanie"):
    st.session_state.strona = 1
    if not plik_excel:
        st.error("Prześlij plik PSZL.xlsx.")
    else:
        pesels = [p.strip() for p in pesel_input.splitlines() if p.strip()]
        niepoprawne = [p for p in pesels if not waliduj_pesel(p)]
        if niepoprawne:
            st.warning(f"Nieprawidłowe PESEL: {', '.join(niepoprawne)}")
        wazne = [p for p in pesels if waliduj_pesel(p)]
        if wazne:
            with st.spinner("Przetwarzanie..."):
                xls = zaladuj_excel(plik_excel.read()); dopasowania = []
                for ark, df in xls.items():
                    df.columns = df.iloc[0]; df = df[1:]
                    if "Ubezpieczony" in df.columns:
                        df["PESEL"] = df["Ubezpieczony"].astype(str).apply(
                            lambda x: re.search(r"(\d{9,13})", x).group(1) if re.search(r"(\d{9,13})", x) else None
                        )
                        traf = df[df["PESEL"].isin(wazne)].copy()
                        if not traf.empty:
                            traf.insert(0, "Arkusz", ark); dopasowania.append(traf)
            st.session_state.wyniki = pd.concat(dopasowania, ignore_index=True) if dopasowania else pd.DataFrame()
            # Log zapytania
            log = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')};{','.join(wazne)};{len(st.session_state.wyniki)}\n"
            with open('query_logs.csv','a',encoding='utf-8') as f: f.write(log)

# === WYŚWIETLANIE WYNIKÓW Z PAGINACJĄ ===
if 'wyniki' in st.session_state:
    df = st.session_state.wyniki.reset_index(drop=True); ile = len(df)
    st.success(f"Znaleziono {ile} rekordów.")
    rozmiar = st.number_input("Rekordów na stronie:", min_value=5, max_value=100, value=10, key='size')
    strony = (ile - 1) // rozmiar + 1
    st.markdown('<div class="pagination">', unsafe_allow_html=True)
    if st.button("← Poprzednia", key='prev') and st.session_state.strona > 1:
        st.session_state.strona -= 1
    st.markdown(f"<span>Strona <b>{st.session_state.strona}</b> z <b>{strony}</b></span>", unsafe_allow_html=True)
    if st.button("Następna →", key='next') and st.session_state.strona < strony:
        st.session_state.strona += 1
    st.markdown('</div>', unsafe_allow_html=True)
    start = (st.session_state.strona - 1) * rozmiar; end = start + rozmiar
    st.write(f"Wyświetlane rekordy {start+1}-{min(end, ile)} z {ile}")
    st.dataframe(df.iloc[start:end])
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine='xlsxwriter') as writer: df.to_excel(writer, index=False)
    buf.seek(0)
    st.download_button("Pobierz wszystkie (Excel)", buf.getvalue(), "wyniki_zwolnienia.xlsx",
                       "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
