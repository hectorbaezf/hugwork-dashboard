import streamlit as st
import pandas as pd
import glob
import matplotlib.pyplot as plt
import calendar

st.set_page_config(layout="wide")

st.title("Dashboard de Uso y Ventas - Hugwork")

# =========================
# CARGAR DATA
# =========================

ruta_ingresos = r"data/ingresos/*.xlsx"

archivos = glob.glob(ruta_ingresos)

df_ingresos = pd.concat(
    [pd.read_excel(f) for f in archivos],
    ignore_index=True
)

df_ingresos["Fecha de reserva"] = pd.to_datetime(df_ingresos["Fecha de reserva"])

df_ingresos["Mes"] = df_ingresos["Fecha de reserva"].dt.to_period("M")

# =========================
# CLASIFICAR PRODUCTO
# =========================

def clasificar_producto(servicio):

    servicio = servicio.lower()

    if "mensualidad" in servicio:
        return "Plan Mensual"

    elif "60 horas" in servicio:
        return "Plan Mensual"

    elif "factura" in servicio:
        return "Pack Horas"

    elif "horas" in servicio:
        return "Pack Horas"

    else:
        return "Hora"

df_ingresos["tipo_producto"] = df_ingresos["Nombre del servicio"].apply(clasificar_producto)

# =========================
# SELECTOR MES
# =========================

meses = sorted(df_ingresos["Mes"].astype(str).unique())

mes = st.selectbox("Seleccionar mes", meses, index=len(meses)-1)

df_mes = df_ingresos[df_ingresos["Mes"].astype(str)==mes]

# =========================
# KPI
# =========================

ingresos = df_mes["Precio del servicio $CLP"].sum()
reservas = len(df_mes)

col1,col2 = st.columns(2)

col1.metric(
    "Ingresos del mes",
    "$" + format(int(ingresos), ",").replace(",", ".")
)

col2.metric(
    "Reservas",
    reservas
)

# =========================
# HISTORICO + PROYECCION
# =========================

historico = df_ingresos.groupby(
    ["Mes","tipo_producto"]
)["Precio del servicio $CLP"].sum().unstack().fillna(0)

historico_m = historico / 1000000

fig, ax = plt.subplots(figsize=(12,5))

historico_m.plot(
    kind="bar",
    stacked=True,
    ax=ax,
    color=["#3E7CB1","#F39237","#2BB673"]
)

# PROYECCION

df_mes_temp = df_ingresos[df_ingresos["Mes"].astype(str)==mes]

ingreso_actual = df_mes_temp["Precio del servicio $CLP"].sum()

dias_transcurridos = df_mes_temp["Fecha de reserva"].dt.day.max()

anio = int(mes.split("-")[0])
mes_num = int(mes.split("-")[1])

dias_mes = calendar.monthrange(anio, mes_num)[1]

proyeccion_total = (ingreso_actual / dias_transcurridos) * dias_mes

ingreso_faltante = proyeccion_total - ingreso_actual

proyeccion_m = ingreso_faltante / 1000000

pos = len(historico_m.index) - 1

ax.bar(
    pos,
    proyeccion_m,
    bottom=historico_m.iloc[pos].sum(),
    color="grey",
    alpha=0.35,
    width=0.6,
    label="Proyección restante"
)

ax.set_title("Ingresos históricos por tipo de arriendo + proyección")

ax.set_ylabel("Millones CLP")

ax.legend()

st.pyplot(fig)

# =========================
# GRAFICOS TORTA
# =========================

col1,col2 = st.columns(2)

# espacio

ingresos_espacio = df_mes.groupby(
    "Nombre de la agenda"
)["Precio del servicio $CLP"].sum()

fig1, ax1 = plt.subplots()

ingresos_espacio.plot.pie(
    autopct="%1.1f%%",
    ax=ax1
)

ax1.set_title("Distribución de ingresos por espacio")

ax1.set_ylabel("")

col1.pyplot(fig1)

# tipo arriendo

ingresos_tipo = df_mes.groupby(
    "tipo_producto"
)["Precio del servicio $CLP"].sum()

fig2, ax2 = plt.subplots()

ingresos_tipo.plot.pie(
    autopct="%1.1f%%",
    colors=["#3E7CB1","#F39237","#2BB673"],
    ax=ax2
)

ax2.set_title("Distribución de ingresos por tipo de arriendo")

ax2.set_ylabel("")

col2.pyplot(fig2)

# =========================
# TOP CLIENTES
# =========================

ranking = df_mes.groupby(
    "Nombre cliente"
).size().reset_index(name="Reservas")

ranking = ranking.sort_values("Reservas", ascending=False).head(5)

st.subheader("Top 5 clientes con mayor uso")

st.dataframe(ranking, use_container_width=True)

# =========================
# SUGERENCIA CAMBIO PLAN
# =========================

def identificar_pack_actual(servicio):

    servicio = servicio.lower()

    if "mensualidad" in servicio:
        return "Plan Mensual"

    elif "60 horas" in servicio:
        return "Pack 60"

    elif "10 horas" in servicio:
        return "Pack 10"

    elif "5 horas" in servicio:
        return "Pack 5"

    else:
        return "Hora"


precio_hora = 6000
pack_10 = 50000
pack_60 = 200000


def evaluar_pack(row):

    gasto_actual = row["gasto"]

    opciones = {
        "Pack 10": pack_10,
        "Pack 60": pack_60
    }

    mejor_pack = "Sin pack"
    costo_pack = gasto_actual
    ahorro = 0

    for pack, precio in opciones.items():

        ahorro_potencial = gasto_actual - precio

        if ahorro_potencial > ahorro:

            mejor_pack = pack
            costo_pack = precio
            ahorro = ahorro_potencial

    return pd.Series([mejor_pack, costo_pack, ahorro])


df_mes["pack_actual"] = df_mes["Nombre del servicio"].apply(identificar_pack_actual)

df_hora = df_mes[df_mes["tipo_producto"] == "Hora"]

uso_clientes = df_hora.groupby("Nombre cliente").agg(
    reservas=("Nombre cliente","count"),
    gasto=("Precio del servicio $CLP","sum"),
    pack_actual=("pack_actual","first")
).reset_index()

uso_clientes["horas"] = uso_clientes["reservas"]

uso_clientes[
    ["pack_recomendado","costo_pack","ahorro"]
] = uso_clientes.apply(
    evaluar_pack,
    axis=1
)

tabla_pack = uso_clientes[
    uso_clientes["pack_recomendado"]!="Sin pack"
].sort_values("ahorro", ascending=False)

st.subheader("Clientes con oportunidad de optimizar su plan")

if len(tabla_pack)>0:

    tabla_pack["Pago actual"] = tabla_pack["gasto"].apply(
        lambda x: "$"+format(int(x),",").replace(",",".")
    )

    tabla_pack["Pago pack"] = tabla_pack["costo_pack"].apply(
        lambda x: "$"+format(int(x),",").replace(",",".")
    )

    tabla_pack["Ahorro estimado"] = tabla_pack["ahorro"].apply(
        lambda x: "$"+format(int(x),",").replace(",",".")
    )

    st.dataframe(
        tabla_pack[
            [
                "Nombre cliente",
                "horas",
                "pack_actual",
                "Pago actual",
                "pack_recomendado",
                "Pago pack",
                "Ahorro estimado"
            ]
        ],
        use_container_width=True
    )