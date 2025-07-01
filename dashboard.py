import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.express as px
import pandas as pd
import sys

# --- 1. Costanti per i Nomi dei File ---
FILE_MOBILITA_SETTIMANALE = 'mobilita_settimanale.csv'
FILE_USERS = 'users.csv'
FILE_FEEDBACK = 'feedback_responses.csv'
FILE_SURVEY = 'survey_responses.csv'

# --- 2. Funzione di Caricamento e Preparazione Dati ---
def load_and_prepare_data():
    """
    Carica tutti i file CSV, li elabora, li unisce e restituisce i DataFrame pronti per l'analisi.
    """
    try:
        # Caricamento mobilità settimanale
        df_settimanale = pd.read_csv(FILE_MOBILITA_SETTIMANALE, dtype={'week_number': str})
        df_settimanale = df_settimanale.rename(columns={'user_id': 'telegram_user_id'})
        df_settimanale['telegram_user_id'] = df_settimanale['telegram_user_id'].astype(int)
        df_settimanale['week_number'] = df_settimanale['week_number'].apply(lambda x: int(x.split('W')[1]))

        # Caricamento utenti
        df_utenti = pd.read_csv(FILE_USERS, header=None)
        df_utenti.columns = ['telegram_user_id', 'user_code', 'language', 'state', 'group']
        df_utenti['telegram_user_id'] = df_utenti['telegram_user_id'].astype(int)

        # Caricamento e merge feedback
        df_feedback = pd.read_csv(FILE_FEEDBACK)
        df_feedback['telegram_user_id'] = df_feedback['telegram_user_id'].astype(int)
        df_feedback_merged = pd.merge(df_feedback, df_utenti, on='telegram_user_id', how='inner')
        df_feedback_merged['answer_1'] = df_feedback_merged['answer_1'].astype(str).str.replace('_t2', '', regex=False)
        df_feedback_merged['answer_2_numeric'] = pd.to_numeric(
            df_feedback_merged['answer_2'].astype(str).str.replace('%', '', regex=False).str.replace(',', '.', regex=False),
            errors='coerce'
        )
        df_feedback_merged['week_number'] = df_feedback_merged['iso_week'].astype(int)

        # Caricamento e merge sondaggi
        df_survey = pd.read_csv(FILE_SURVEY)
        df_survey = df_survey.rename(columns={'user_id': 'telegram_user_id'})
        df_survey['telegram_user_id'] = df_survey['telegram_user_id'].astype(int)
        df_survey['response_date'] = pd.to_datetime(df_survey['response_date'])
        df_survey['week_number'] = df_survey['response_date'].dt.isocalendar().week.astype(int)
        df_survey_merged = pd.merge(df_survey, df_utenti, on='telegram_user_id', how='inner')

        # Preparazione dati mobilità finale
        df_merged = pd.merge(df_settimanale, df_utenti, on='telegram_user_id', how='inner')
        movement_columns = ['walking', 'in bus', 'in train', 'in passenger vehicle', 'running', 'cycling']
        df_merged = df_merged[~(df_merged[movement_columns] == 0).all(axis=1)]

        # --- Preparazione dati per Matrice di Correlazione ---
        df_survey_numeric = df_survey_merged.copy()
        
        response_map = {
            'Mai': 0, 'Raramente': 1, 'A volte': 2,
            'Meno della metà del tempo': 3, 'Più della metà del tempo': 4,
            'La maggior parte nel tempo': 5, 'La maggior parte dei giorni': 5,
            'Sempre': 6, 'Ogni giorno': 6
        }

        questions_to_map = ['answer_1', 'answer_2', 'answer_3', 'answer_4', 'answer_5', 'answer_6', 'answer_7']
        for col in questions_to_map:
            df_survey_numeric[col] = df_survey_numeric[col].replace(response_map)
            df_survey_numeric[col] = pd.to_numeric(df_survey_numeric[col], errors='coerce')

        df_survey_numeric['wellbeing_score'] = df_survey_numeric[['answer_1', 'answer_2', 'answer_3', 'answer_4', 'answer_5']].sum(axis=1, skipna=True)
        
        # Seleziona e rinomina le colonne per la matrice di correlazione
        correlation_data = df_survey_numeric[['telegram_user_id', 'week_number', 'wellbeing_score', 'answer_6', 'answer_7']]
        correlation_data = correlation_data.rename(columns={'answer_6': 'dolci', 'answer_7': 'carne_rossa'})

        df_all_data = pd.merge(
            df_merged,
            correlation_data,
            on=['telegram_user_id', 'week_number'],
            how='inner'
        )

        return df_merged, df_feedback_merged, df_survey_merged, df_all_data, movement_columns

    except FileNotFoundError as e:
        print(f"Errore: file non trovato - {e.filename}. Assicurati che tutti i file CSV siano presenti.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Si è verificato un errore durante la preparazione dei dati: {e}", file=sys.stderr)
        sys.exit(1)


# --- 3. Caricamento Dati Globale ---
df_merged, df_feedback_merged, df_survey_merged, df_all_data, movement_columns = load_and_prepare_data()

# Ordina le settimane e crea i label per lo slider
sorted_weeks = sorted(df_merged['week_number'].unique())
week_labels = {i: str(week) for i, week in enumerate(sorted_weeks)}

# --- 4. Mappatura Domande Sondaggio ---
survey_question_map = {
    "answer_1": "Mi sono sentito/a allegro/a e di buon umore",
    "answer_2": "Mi sono sentito/a calmo/a e rilassato/a",
    "answer_3": "Mi sono sentito/a attivo/a ed energico/a",
    "answer_4": "Mi sono svegliato/a sentendomi fresco/a e riposato/a",
    "answer_5": "La mia vita di tutti i giorni è stata piena di cose che mi interessano",
    "answer_6": "Nell’ultima settimana quante volte hai mangiato dolci?",
    "answer_7": "Nell’ultima settimana quante volte hai mangiato carne rossa?"
}
survey_questions = list(survey_question_map.keys())


# --- 5. Inizializzazione dell'App Dash ---
app = dash.Dash(__name__)
server = app.server
app.title = "Dashboard Mobilità Sostenibile"

# --- 6. Definizione del Layout dell'Applicazione ---
kpi_card_style = {
    'padding': '20px', 'margin': '10px', 'border-radius': '5px',
    'background-color': '#f9f9f9', 'box-shadow': '0 2px 4px rgba(0,0,0,0.1)',
    'text-align': 'center', 'flex': '1'
}

app.layout = html.Div(children=[
    html.H1('Analisi Interattiva della Mobilità', style={'textAlign': 'center', 'color': '#333'}),

    html.Div([
        html.H4('Seleziona Intervallo Settimane', style={'textAlign': 'center'}),
        dcc.RangeSlider(
            id='week-slider', min=0, max=len(sorted_weeks) - 1,
            value=[0, len(sorted_weeks) - 1], marks=week_labels, step=1
        )
    ], style={'padding': '20px 50px'}),

    html.Div(id='kpi-container', style={'display': 'flex', 'justify-content': 'space-around', 'margin-bottom': '30px'}),
    html.Hr(),

    html.Div([
        html.Div([
            html.H4('Andamento Temporale Mobilità', style={'textAlign': 'center'}),
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
        html.Div([
            html.H4('Composizione Media Mobilità nel Periodo', style={'textAlign': 'center'}),
            dcc.Graph(id='composition-bar-chart')
        ], style={'flex': '1', 'padding': '10px'})
    ], style={'display': 'flex'}),

    html.Hr(),
    
    html.Div([
        html.H2('Matrice di Correlazione tra le Variabili', style={'textAlign': 'center', 'color': '#333', 'margin-top': '40px'}),
        dcc.Graph(id='correlation-matrix-heatmap')
    ], style={'padding': '20px'}),

    html.Hr(),

    html.Div([
        html.H2('Analisi Feedback e Sondaggi', style={'textAlign': 'center', 'color': '#333', 'margin-top': '40px', 'margin-bottom': '20px'}),
        html.Div([
            html.Div([
                html.H4('Seleziona Tipo di Analisi Feedback', style={'textAlign': 'center', 'margin-bottom': '15px'}),
                dcc.Dropdown(
                    id='feedback-analysis-selector',
                    options=[
                        {'label': 'Hai intenzione di migliorare?', 'value': 'answer_1'},
                        {'label': 'Fissa un obiettivo', 'value': 'answer_2_numeric'}
                    ],
                    value='answer_1', clearable=False, style={'margin-bottom': '10px'}
                ),
                dcc.Graph(id='feedback-analysis-graph')
            ], style={'flex': '1', 'padding': '10px'}),
            html.Div([
                html.H4('Analisi Risposte Sondaggio', style={'textAlign': 'center', 'margin-bottom': '15px'}),
                dcc.Dropdown(
                    id='survey-question-dropdown',
                    options=[{'label': survey_question_map.get(q, q), 'value': q} for q in survey_questions],
                    value=survey_questions[0] if survey_questions else None,
                    clearable=False, style={'margin-bottom': '10px'}
                ),
                dcc.Graph(id='survey-bar-chart')
            ], style={'flex': '1', 'padding': '10px'})
        ], style={'display': 'flex', 'padding': '0 20px'})
    ], style={'padding': '20px'}),
])

# --- 7. Logica di Callback ---

@app.callback(
    [Output('kpi-container', 'children'),
     Output('mobility-graph', 'figure'),
     Output('composition-bar-chart', 'figure')],
    [Input('week-slider', 'value'),
     Input('metric-selector', 'value')]
)
def update_mobility_dashboard(week_range, selected_metric):
    start_week_idx, end_week_idx = week_range
    start_week = sorted_weeks[start_week_idx]
    end_week = sorted_weeks[end_week_idx]
    filtered_df = df_merged[(df_merged['week_number'] >= start_week) & (df_merged['week_number'] <= end_week)]

    if not filtered_df.empty:
        percent_sustainable = filtered_df['percent_sustainable'].mean()
        # Definizione delle colonne per mobilità sostenibile e non sostenibile
        sustainable_cols = ['walking', 'cycling', 'in bus', 'in train', 'running']
        non_sustainable_cols = ['in passenger vehicle']

        # Calcolo delle distanze medie
        avg_sustainable_distance = filtered_df[sustainable_cols].sum(axis=1).mean()
        avg_non_sustainable_distance = filtered_df[non_sustainable_cols].sum(axis=1).mean()

        best_group_series = filtered_df.groupby('group')['percent_sustainable'].mean()
        best_group = best_group_series.idxmax() if not best_group_series.empty else 'N/A'
        best_group_value = best_group_series.max() if not best_group_series.empty else 0
    else:
        percent_sustainable, avg_sustainable_distance, avg_non_sustainable_distance, best_group, best_group_value = 0, 0, 0, 'N/A', 0

    kpi_cards = [
        html.Div([html.H3(f"{percent_sustainable:.2f}%", style={'color': '#007BFF'}), html.P("Sostenibilità Media")], style=kpi_card_style),
        html.Div([html.H3(f"{avg_sustainable_distance:,.0f} km", style={'color': '#28A745'}), html.P("Distanza Media Sostenibile")], style=kpi_card_style),
        html.Div([html.H3(f"{avg_non_sustainable_distance:,.0f} km", style={'color': '#DC3545'}), html.P("Distanza Media Non Sostenibile")], style=kpi_card_style),
        html.Div([html.H3(f"Gruppo {best_group}", style={'color': '#FFC107'}), html.P(f"Più Virtuoso ({best_group_value:.2f}%)")], style=kpi_card_style),
    ]

    line_df = filtered_df.groupby(['week_number', 'group'])[selected_metric].mean().reset_index()
    line_fig = px.line(line_df, x='week_number', y=selected_metric, color='group', markers=True,
                     title=f'Andamento: {selected_metric}', labels={'week_number': 'Settimana', selected_metric: 'Valore Medio', 'group': 'Gruppo'},
                     template='plotly_white')
    line_fig.update_layout(legend_title='Gruppi')

    melted_df = filtered_df.melt(id_vars=['group'], value_vars=movement_columns, var_name='Mezzo', value_name='Distanza (km)')
    bar_df = melted_df.groupby(['group', 'Mezzo'])['Distanza (km)'].mean().reset_index()
    bar_fig = px.bar(bar_df, x='group', y='Distanza (km)', color='Mezzo', barmode='group',
                     title='Composizione Media della Mobilità', labels={'group': 'Gruppo', 'Distanza (km)': 'Distanza Media (km)'},
                     template='plotly_white')
    bar_fig.update_layout(legend_title='Mezzo')

    return kpi_cards, line_fig, bar_fig

@app.callback(
    Output('correlation-matrix-heatmap', 'figure'),
    [Input('week-slider', 'value')]
)
def update_correlation_matrix(week_range):
    start_week_idx, end_week_idx = week_range
    start_week = sorted_weeks[start_week_idx]
    end_week = sorted_weeks[end_week_idx]

    filtered_df = df_all_data[
        (df_all_data['week_number'] >= start_week) &
        (df_all_data['week_number'] <= end_week)
    ]

    if filtered_df.empty:
        return px.imshow(title="Nessun dato disponibile per la matrice di correlazione")

    # Seleziona solo le colonne numeriche per la correlazione
    cols_for_corr = ['percent_sustainable', 'total', 'walking', 'cycling', 'running', 'wellbeing_score', 'dolci', 'carne_rossa']
    corr_matrix = filtered_df[cols_for_corr].corr()

    fig = px.imshow(
        corr_matrix,
        text_auto=True,
        aspect="auto",
        color_continuous_scale='RdBu_r', # Scala di colori Rosso-Blu
        zmin=-1, zmax=1, # Fissa il range di colori da -1 a 1
        title='Matrice di Correlazione tra Mobilità, Benessere e Abitudini'
    )
    fig.update_xaxes(side="top")
    return fig

@app.callback(
    Output('feedback-analysis-graph', 'figure'),
    [Input('feedback-analysis-selector', 'value'),
     Input('week-slider', 'value')]
)
def update_feedback_analysis_graph(selected_feedback_metric, week_range):
    start_week_idx, end_week_idx = week_range
    start_week = sorted_weeks[start_week_idx]
    end_week = sorted_weeks[end_week_idx]
    
    filtered_df_feedback = df_feedback_merged[
        (df_feedback_merged['week_number'] >= start_week) &
        (df_feedback_merged['week_number'] <= end_week)
    ]

    if filtered_df_feedback.empty:
        return px.bar(title='Nessun dato disponibile per il feedback selezionato nel periodo')

    if selected_feedback_metric == 'answer_1':
        counts = filtered_df_feedback.groupby(['group', 'answer_1']).size().reset_index(name='Count')
        fig = px.bar(counts, x='answer_1', y='Count', color='group', facet_col='group',
                     title='Hai intenzione di migliorare? (per Gruppo)', labels={'answer_1': 'Risposta', 'Count': 'Numero di Risposte', 'group': 'Gruppo'},
                     template='plotly_white')
        fig.update_layout(showlegend=False)
    elif selected_feedback_metric == 'answer_2_numeric':
        fig = px.box(filtered_df_feedback, x='group', y='answer_2_numeric', color='group',
                     title='Obiettivo fissato (per Gruppo)', labels={'answer_2_numeric': 'Valore Obiettivo (%)', 'group': 'Gruppo'},
                     template='plotly_white')
    else:
        fig = px.bar(title='Seleziona una metrica di feedback')

    return fig

@app.callback(
    Output('survey-bar-chart', 'figure'),
    [Input('survey-question-dropdown', 'value'),
     Input('week-slider', 'value')]
)
def update_survey_chart(selected_question, week_range):
    if not selected_question:
        return px.bar(title='Seleziona una domanda per visualizzare i risultati')

    start_week_idx, end_week_idx = week_range
    start_week = sorted_weeks[start_week_idx]
    end_week = sorted_weeks[end_week_idx]
    
    filtered_survey_df = df_survey_merged[
        (df_survey_merged['week_number'] >= start_week) & 
        (df_survey_merged['week_number'] <= end_week)
    ]

    if filtered_survey_df.empty:
        question_text = survey_question_map.get(selected_question, selected_question)
        return px.bar(title=f'Nessun dato per: "{question_text}"')

    response_counts = filtered_survey_df.groupby(['group', selected_question]).size().reset_index(name='Count')
    response_counts.columns = ['Group', 'Response', 'Count']
    question_text = survey_question_map.get(selected_question, selected_question)

    fig = px.bar(response_counts, x='Response', y='Count', color='Group', facet_col='Group',
                 title=f'Risposte per: "{question_text}"', labels={'Response': 'Risposta', 'Count': 'Numero di Risposte', 'Group': 'Gruppo'},
                 template='plotly_white')
    fig.update_layout(showlegend=False)
    return fig


# --- 8. Avvio del Server ---
if __name__ == '__main__':
    app.run(debug=True)
