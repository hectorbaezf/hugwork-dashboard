import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import glob
import calendar

# ======================
# CONFIG
# ======================
st.set_page_config(layout="wide")

# ======================
# CARGA DE DATOS
# ======================
ruta = "data/ingresos/*.xlsx"
archivos = glob.glob(ruta)

df_ingresos = pd.concat([pd.read_excel(f) for f in archivos], ignore_index=True)

# ======================
# NORMALIZACIÓN
# ======================
df_ingresos.columns = df_ingresos.columns.str.strip()

df_ingresos = df_ingresos.rename(columns={
    "Fecha de la reserva": "Fecha de reserva",
    "Nombre del cliente": "Nombre cliente",
    "Ingreso": "Precio del servicio $CLP"
})

df_ingresos["Fecha de reserva"] = pd.to_datetime(df_ingresos["Fecha de reserva"])

df_ingresos["Mes"] = df_ingresos["Fecha de reserva"].dt.to_period("M").astype(str)

# ======================
# CLASIFICACIÓN PRODUCTO
# ======================
def clasificar_producto(servicio):
    servicio = str(servicio).lower()

    if "mensual" in servicio:
        return "Plan Mensual"
    elif "pack" in servicio:
        return "Pack Horas"
    else:
        return "Hora"

df_ingresos["tipo_producto"] = df_ingresos["Nombre del servicio"].apply(clasificar_producto)

# ======================
# SELECTOR MES
# ======================
meses = sorted(df_ingresos["Mes"].unique())
mes = st.selectbox("Selecciona mes", meses, index=len(meses)-1)

df_mes = df_ingresos[df_ingresos["Mes"] == mes]

# ======================
# KPIs
# ======================
ingresos = df_mes["Precio del servicio $CLP"].sum()
reservas = len(df_mes)

col1, col2 = st.columns(2)

col1.metric("Ingresos del mes", f"${ingresos:,.0f}".replace(",", "."))
col2.metric("Reservas", reservas)

# ======================
# PROYECCIÓN
# ======================
dias_transcurridos = df_mes["Fecha de reserva"].dt.day.max()

anio = int(mes.split("-")[0])
mes_num = int(mes.split("-")[1])
dias_mes = calendar.monthrange(anio, mes_num)[1]

proyeccion = (ingresos / dias_transcurridos) * dias_mes

# ======================
# HISTÓRICO
# ======================
df_hist = df_ingresos.groupby(["Mes", "tipo_producto"])["Precio del servicio $CLP"].sum().unstack().fillna(0)
df_hist_millones = df_hist / 1_000_000

fig, ax = plt.subplots(figsize=(12,5))

df_hist_millones.plot(kind="bar", stacked=True, ax=ax)

ultimo_mes = df_hist_millones.index[-1]

# SOLO proyección restante (gris)
ax.bar(
    ultimo_mes,
    (proyeccion/1_000_000) - df_hist_millones.loc[ultimo_mes].sum(),
    bottom=df_hist_millones.loc[ultimo_mes].sum(),
    color="gray",
    label="Proyección restante"
)

ax.set_ylabel("Millones CLP")
ax.set_title("Ingresos históricos por tipo de arriendo + proyección")
ax.legend()

st.pyplot(fig)

# ======================
# GRÁFICOS
# ======================
col1, col2 = st.columns(2)

# POR ESPACIO
espacio = df_mes.groupby("Nombre de la agenda")["Precio del servicio $CLP"].sum()

fig1, ax1 = plt.subplots()
ax1.pie(espacio, labels=espacio.index, autopct="%1.1f%%")
ax1.set_title("Ingresos por espacio")

col1.pyplot(fig1)

# POR TIPO
tipo = df_mes.groupby("tipo_producto")["Precio del servicio $CLP"].sum()

fig2, ax2 = plt.subplots()
ax2.pie(tipo, labels=tipo.index, autopct="%1.1f%%")
ax2.set_title("Ingresos por tipo de arriendo")

col2.pyplot(fig2)

# ======================
# TOP CLIENTES
# ======================
st.subheader("Top 5 clientes")

top_clientes = df_mes.groupby("Nombre cliente").size().sort_values(ascending=False).head(5)
st.dataframe(top_clientes)

# ======================
# PACK RECOMENDACIÓN
# ======================
st.subheader("Clientes con oportunidad de cambio de plan")

precio_hora = 6000
pack_10 = 50000

uso = df_mes.groupby("Nombre cliente").agg(
    reservas=("Nombre cliente", "count"),
    gasto=("Precio del servicio $CLP", "sum")
).reset_index()

uso["horas"] = uso["reservas"]

def evaluar(row):
    gasto_actual = row["gasto"]
    horas = row["horas"]

    costo_pack = pack_10
    ahorro = gasto_actual - costo_pack

    if ahorro > 0:
        return pd.Series(["Pack 10", costo_pack, ahorro])
    else:
        return pd.Series(["Sin pack", gasto_actual, 0])

uso[["pack_recomendado", "costo_pack", "ahorro"]] = uso.apply(evaluar, axis=1)

tabla = uso[uso["pack_recomendado"] != "Sin pack"].sort_values("ahorro", ascending=False)

tabla["pago_actual"] = tabla["gasto"].apply(lambda x: f"${x:,.0f}".replace(",", "."))
tabla["pago_pack"] = tabla["costo_pack"].apply(lambda x: f"${x:,.0f}".replace(",", "."))
tabla["ahorro_fmt"] = tabla["ahorro"].apply(lambda x: f"${x:,.0f}".replace(",", "."))

st.dataframe(tabla[[
    "Nombre cliente",
    "horas",
    "pago_actual",
    "pack_recomendado",
    "pago_pack",
    "ahorro_fmt"
]])