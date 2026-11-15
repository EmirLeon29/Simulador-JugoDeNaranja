# 🍊 Balance de materia · Planta de zumo de naranja

Simulador interactivo (Streamlit) del balance de materia de una planta de zumo de naranja:
selección, lavado, extracción y subproductos, con comparación contra la línea base.

## Ejecutar en local

```bash
python -m venv .venv
source .venv/bin/activate        # En Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

## Desplegar gratis

1. Sube este repositorio a GitHub.
2. Entra en [share.streamlit.io](https://share.streamlit.io), conecta tu cuenta de GitHub.
3. Elige el repositorio, la rama y `app.py` como archivo principal.

## Estructura

- `app.py`: interfaz y motor de cálculo
- `requirements.txt`: dependencias
