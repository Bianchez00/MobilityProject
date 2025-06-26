import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.express as px
import pandas as pd

# --- 1. Caricamento e Preparazione Dati ---

try:
    df_settimanale = pd.read_csv('mobilita_settimanale.csv')
    df_utenti = pd.read_csv('users.csv')
except FileNotFoundError:
    print("Assicurati che i file 'mobilita_settimanale.csv' e 'users.csv' siano nella stessa cartella.")
    exit()

df_utenti.columns = ['user_id', 'telegram_user_id', 'language', 'state', 'group']
df_merged = pd.merge(df_settimanale, df_utenti, on='user_id', how='inner')
movement_columns = ['walking', 'in bus', 'in train', 'in passenger vehicle', 'running', 'cycling']
df_merged = df_merged[~(df_merged[movement_columns] == 0).all(axis=1)]

# Ordina le settimane e crea i label per lo slider
sorted_weeks = sorted(df_merged['week_number'].unique())
week_labels = {i: week for i, week in enumerate(sorted_weeks)}

# --- 2. Inizializzazione dell'App Dash ---
app = dash.Dash(__name__)
server = app.server
app.title = "Dashboard Mobilità Sostenibile"

# --- 3. Definizione del Layout dell'Applicazione ---

kpi_card_style = {
    'padding': '20px',
    'margin': '10px',
    'border-radius': '5px',
    'background-color': '#f9f9f9',
    'box-shadow': '0 2px 4px rgba(0,0,0,0.1)',
    'text-align': 'center',
    'flex': '1'
}

app.layout = html.Div(children=[
    html.H1('Analisi Interattiva della Mobilità', style={'textAlign': 'center', 'color': '#333'}),

    # Selettore Intervallo Temporale
    html.Div([
        html.H4('Seleziona Intervallo Settimane', style={'textAlign': 'center'}),
        dcc.RangeSlider(
            id='week-slider',
            min=0,
            max=len(sorted_weeks) - 1,
            value=[0, len(sorted_weeks) - 1],
            marks=week_labels,
            step=1
        )
    ], style={'padding': '20px 50px'}),

    # Sezione KPI Dinamici
    html.Div(id='kpi-container', style={'display': 'flex', 'justify-content': 'space-around', 'margin-bottom': '30px'}),

    html.Hr(),

    # Sezione Grafici
    html.Div([
        # Grafico a Linee
        html.Div([
            html.H4('Andamento Temporale', style={'textAlign': 'center'}),
            dcc.RadioItems(
                id='metric-selector',
                options=[
                    {'label': 'Sostenibilità %', 'value': 'percent_sustainable'},
                    {'label': 'Distanza Totale', 'value': 'total'},
                    {'label': 'Camminata', 'value': 'walking'},
                    {'label': 'Bici', 'value': 'cycling'},
                ],
                value='percent_sustainable',
                labelStyle={'display': 'inline-block', 'margin-right': '15px'},
                style={'textAlign': 'center', 'margin-bottom': '10px'}
            ),
            dcc.Graph(id='mobility-graph')
        ], style={'flex': '1', 'padding': '10px'}),

        # Grafico a Barre
        html.Div([
            html.H4('Composizione Media nel Periodo', style={'textAlign': 'center'}),
            dcc.Graph(id='composition-bar-chart')
        ], style={'flex': '1', 'padding': '10px'})
    ], style={'display': 'flex'})
])

# --- 4. Logica di Callback Unificata ---

@app.callback(
    [
        Output('kpi-container', 'children'),
        Output('mobility-graph', 'figure'),
        Output('composition-bar-chart', 'figure')
    ],
    [
        Input('week-slider', 'value'),
        Input('metric-selector', 'value')
    ]
)
def update_dashboard(week_range, selected_metric):
    # Filtra il DataFrame in base al RangeSlider
    start_week = sorted_weeks[week_range[0]]
    end_week = sorted_weeks[week_range[1]]
    filtered_df = df_merged[(df_merged['week_number'] >= start_week) & (df_merged['week_number'] <= end_week)]

    # --- 1. Aggiornamento KPI ---
    percent_sustainable = filtered_df['percent_sustainable'].mean()
    total_distance = filtered_df['total'].sum()
    best_group_series = filtered_df.groupby('group')['percent_sustainable'].mean()
    best_group = best_group_series.idxmax() if not best_group_series.empty else 'N/A'
    best_group_value = best_group_series.max() if not best_group_series.empty else 0

    kpi_cards = [
        html.Div([html.H3(f"{percent_sustainable:.2f}%", style={'color': '#007BFF'}), html.P("Sostenibilità Media")], style=kpi_card_style),
        html.Div([html.H3(f"{total_distance:,.0f} km", style={'color': '#28A745'}), html.P("Distanza Totale")       ], style=kpi_card_style),
        html.Div([html.H3(f"Gruppo {best_group}", style={'color': '#FFC107'}), html.P(f"Più Virtuoso ({best_group_value:.2f}%)")], style=kpi_card_style),
    ]

    # --- 2. Aggiornamento Grafico a Linee ---
    line_df = filtered_df.groupby(['week_number', 'group'])[selected_metric].mean().reset_index()
    line_fig = px.line(
        line_df, x='week_number', y=selected_metric, color='group', markers=True,
        title=f'Andamento: {selected_metric}',
        labels={'week_number': 'Settimana', selected_metric: 'Valore Medio', 'group': 'Gruppo'},
        template='plotly_white'
    )
    line_fig.update_layout(legend_title='Gruppi')

    # --- 3. Aggiornamento Grafico a Barre ---
    melted_df = filtered_df.melt(id_vars=['group'], value_vars=movement_columns, var_name='Mezzo', value_name='Distanza (km)')
    bar_df = melted_df.groupby(['group', 'Mezzo'])['Distanza (km)'].mean().reset_index()
    bar_fig = px.bar(
        bar_df, x='group', y='Distanza (km)', color='Mezzo', barmode='group',
        title='Composizione Media della Mobilità',
        labels={'group': 'Gruppo', 'Distanza (km)': 'Distanza Media (km)'},
        template='plotly_white'
    )
    bar_fig.update_layout(legend_title='Mezzo')

    return kpi_cards, line_fig, bar_fig

# --- 5. Avvio del Server ---
if __name__ == '__main__':
    app.run(debug=True)