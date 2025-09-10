# -*- coding: utf-8 -*-
import pandas as pd
from pandas import read_csv, ExcelWriter
import matplotlib.pyplot as plt
import plotly.express as px
from dash import Dash, html, dcc, Output, Input, State, callback_context
import datetime
from datetime import datetime, timedelta
from collections import defaultdict

app = Dash(__name__)
server = app.server

path_NFS_NFE = "NFS+NFE Commissioning Dashboard_All positions.xlsx"

# Lecture des fichiers
nfe_df = pd.read_excel(path_NFS_NFE, sheet_name="NFE Dashboard_Jul 25", engine="openpyxl")
nfs_df = pd.read_excel(path_NFS_NFE, sheet_name="NFS Dashboard", engine="openpyxl")

# Traitement NFE
nfe_df = nfe_df[['BarChart Demob Date', 'Discipline', "Candidate'a name", "JOB TITLE per manning"]].copy()
nfe_df['Type'] = 'Demob NFE'

# Sauver la vraie date de démobilisation
nfe_df['Original Demob Date'] = pd.to_datetime(nfe_df['BarChart Demob Date'], errors="coerce")
# Utiliser une version décalée pour l'affichage du graphe
nfe_df['Date'] = nfe_df['Original Demob Date'] + pd.DateOffset(months=1)

# Traitement NFS
nfs_df = nfs_df[['BarChart Mob Date', 'Discipline', "JOB TITLE per manning"]].copy()
nfs_df['Type'] = 'Mobilisation NFS'
nfs_df.rename(columns={'BarChart Mob Date': 'Date'}, inplace=True)
nfs_df['Date'] = pd.to_datetime(nfs_df['Date'], errors="coerce")

# Fusion
combined_df = pd.concat([nfe_df, nfs_df], ignore_index=True)
combined_df = combined_df.dropna(subset=['Date'])
combined_df['Month'] = combined_df['Date'].dt.to_period('M').astype(str)

combined_df = combined_df[(combined_df['Type'] != 'Demob NFE')|(combined_df['Date'] >= pd.Timestamp("2025-08-01"))]
combined_df = combined_df[combined_df['Discipline'] != "Building / HVAC"]

all_months = pd.period_range(
    start=combined_df['Date'].min().to_period('M'),
    end=combined_df['Date'].max().to_period('M'),
    freq='M'
).astype(str).tolist()

annees_mois_global = defaultdict(list)
for m in all_months:
    p = pd.Period(m, freq='M')
    annees_mois_global[p.year].append(m)
bornes_annuelles = [mois_list[-1] for mois_list in annees_mois_global.values()]

"""## graph 2"""

# Layout principal
app.layout = html.Div([
    html.H2("PCCSU DEMOB NFE vs MOB NFS Dashboard", style={
        'textAlign': 'center',
        'fontSize': '32px',
        'fontWeight': '600',
        'marginBottom': '20px',
        'fontFamily': 'Helvetica, Arial, sans-serif',
        'color': '#2c3e50'
    }),

    html.Div([
        html.Label("Filter by discipline:", style={
            'textAlign': 'center',
            'display': 'block',
            'fontSize': '18px',
            'fontWeight': '500',
            'color': '#555',
            'marginBottom': '8px',
            'fontFamily': 'Arial'
        }),
        dcc.Dropdown(
            options=[{"label": "All disciplines", "value": "ALL"}] +
                    [{"label": d, "value": d} for d in sorted(combined_df['Discipline'].unique())],
            value="ALL", id='discipline-filter',
            style={
                'width': '400px',
                'margin': '0 auto 30px',
                'fontSize': '16px',
                'borderRadius': '5px',
                'boxShadow': '0 1px 4px rgba(0,0,0,0.1)'
            }
        )
    ]),

    dcc.Store(id='sort-direction', data='asc'),
    dcc.Store(id='sort-direction2', data='asc'),

    html.Div([
        dcc.Graph(id='stacked-histogram', style={
            'flex': '2', 'height': '600px',
            'padding': '10px',
            'borderRadius': '10px',
            'boxShadow': '0 2px 8px rgba(0,0,0,0.1)',
            'backgroundColor': '#fafafa'
        }),

        html.Div([
            html.Div(id='selected-month-display', style={
                'fontSize': '16px',
                'color': '#2c3e50',
                'marginBottom': '15px',
                'fontStyle': 'italic',
                'textAlign': 'center',
                'backgroundColor': '#f2f2f2',
                'padding': '8px',
                'borderRadius': '6px',
                'boxShadow': '0 1px 3px rgba(0,0,0,0.05)',
                'fontFamily': 'Helvetica, Arial, sans-serif'
            }),

            html.H4("🟩 Demobilisation List", style={
                'fontSize': '20px', 'fontWeight': '600',
                'color': '#2c3e50', 'marginBottom': '10px',
                'borderBottom': '2px solid #dfe6e9',
                'paddingBottom': '5px'
            }),

            html.Table([
                html.Thead(html.Tr([
                    html.Th("Name", style={'backgroundColor': '#34495e', 'color': 'white', 'padding': '8px'}),
                    html.Th([
                        "Demob Date ",
                        html.Button("⇅", id='sort-button', n_clicks=0, style={
                            'background': 'none', 'border': 'none', 'cursor': 'pointer',
                            'fontSize': '16px', 'color': 'white'
                        })
                    ], style={'backgroundColor': '#34495e', 'color': 'white', 'padding': '8px'}),
                    html.Th("Job Title", style={'backgroundColor': '#34495e', 'color': 'white', 'padding': '8px'})
                ])),
                html.Tbody(id='table-body')
            ], style={
                'width': '100%',
                'borderCollapse': 'collapse',
                'marginBottom': '30px',
                'fontFamily': 'Arial',
                'backgroundColor': '#fff'
            }),

            html.H4("🟥 Mobilisation List", style={
                'fontSize': '20px', 'fontWeight': '600',
                'color': '#2c3e50', 'marginBottom': '10px',
                'borderBottom': '2px solid #dfe6e9',
                'paddingBottom': '5px'
            }),

            html.Table([
                html.Thead(html.Tr([
                    html.Th([
                        "Mob Date ",
                        html.Button("⇅", id='sort-button2', n_clicks=0, style={
                            'background': 'none', 'border': 'none', 'cursor': 'pointer',
                            'fontSize': '16px', 'color': 'white'
                        })
                    ], style={'backgroundColor': '#34495e', 'color': 'white', 'padding': '8px'}),
                    html.Th("Job Title", style={'backgroundColor': '#34495e', 'color': 'white', 'padding': '8px'})
                ])),
                html.Tbody(id='mob-table-body')
            ], style={
                'width': '100%',
                'borderCollapse': 'collapse',
                'fontFamily': 'Arial',
                'backgroundColor': '#fff'
            })
        ], style={
            'flex': '1',
            'padding': '20px',
            'borderRadius': '10px',
            'boxShadow': '0 2px 8px rgba(0,0,0,0.05)',
            'backgroundColor': '#fefefe',
            'marginLeft': '20px',
            'height': '600px',
            'overflowY': 'auto'
        })
    ], style={'display': 'flex', 'gap': '20px'})
])


# Callback du graphique
@app.callback(
    Output('stacked-histogram', 'figure'),
    Input('discipline-filter', 'value')
)
def update_graph(selected_discipline):
    if selected_discipline == "ALL":
        filtered = combined_df.copy()
    else:
        filtered = combined_df[combined_df['Discipline'] == selected_discipline]

    grouped = filtered.groupby(['Month', 'Type']).size().reset_index(name='Count')

    fig = px.bar(
        grouped,
        x='Month',
        y='Count',
        color='Type',
        title=f"Stacked Histogram : {selected_discipline}",
        labels={'Count': 'Demob/Mob', 'Month': 'Date'},
        barmode='stack',
        color_discrete_map={
            'Mobilisation NFS': '#b33232',
            'Demob NFE': '#52ce83'
        }
    )

    # Lignes verticales à fin d'année
    vertical_lines = []
    for dernier_mois in bornes_annuelles:
        date_obj = pd.Period(dernier_mois, freq='M').to_timestamp()
        date_center = date_obj + timedelta(days=15)
        vertical_lines.append(dict(
            type='line',
            x0=date_center,
            x1=date_center,
            y0=0,
            y1=1,
            xref='x',
            yref='paper',
            line=dict(color='gray', width=1, dash='dot')
        ))

    # Annotations années en haut
    months_sorted = sorted(set(grouped['Month']))
    periods = [pd.Period(m, freq='M') for m in months_sorted]
    annees_mois = defaultdict(list)
    for p in periods:
        annees_mois[p.year].append(p.strftime('%Y-%m'))
    annees_sorted = sorted(annees_mois.keys())
    annotations = []
    for i, annee in enumerate(annees_sorted):
        try:
            mois_debut = bornes_annuelles[i - 1] if i > 0 else annees_mois[annee][0]
            mois_fin = bornes_annuelles[i]
            date_debut = pd.Period(mois_debut, freq='M').to_timestamp()
            date_fin = pd.Period(mois_fin, freq='M').to_timestamp()
            date_centre = date_debut + (date_fin - date_debut) / 2
        except IndexError:
            continue
        annotations.append(dict(
            x=date_centre,
            y=1.0,
            text=str(annee),
            showarrow=False,
            xanchor='center',
            yanchor='bottom',
            font=dict(size=14, color='black'),
            xref='x',
            yref='paper'
        ))

    formatted_months = [pd.Period(m, freq='M').strftime('%b').upper() for m in all_months]

    fig.update_layout(
        annotations=annotations,
        shapes=vertical_lines,
        margin=dict(t=60),
        bargap=0.2,
        xaxis=dict(
            tickangle=-45,
            tickfont=dict(size=11),
            tickmode='array',
            tickvals=all_months,
            ticktext=formatted_months
        ),
        clickmode='event+select'
    )
    fig.update_traces(hovertemplate='<b>Month:</b> %{x}<br><b>Count:</b> %{y}<extra></extra>')
    fig.write_html("graphique_interactif.html")

    return fig

@app.callback(
    Output('table-body', 'children'),
    Output('mob-table-body', 'children'),
    Output('sort-direction', 'data'),
    Output('sort-direction2', 'data'),
    Output('selected-month-display', 'children'),
    Input('stacked-histogram', 'clickData'),
    Input('discipline-filter', 'value'),
    Input('sort-button', 'n_clicks'),
    Input('sort-button2', 'n_clicks'),
    State('sort-direction', 'data'),
    State('sort-direction2', 'data')
)
def show_names(clickData, selected_discipline, n_clicks_demob, n_clicks_mob, current_sort, current_sort2):
    type_demob = 'Demob NFE'
    type_mob = 'Mobilisation NFS'

    # 🔍 Identifier le déclencheur
    ctx = callback_context
    triggered_id = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else None

    # 🗓️ Mois sélectionné
    mois = None
    if clickData and 'points' in clickData:
        try:
            mois = pd.to_datetime(clickData['points'][0]['x']).to_period('M').strftime('%Y-%m')
        except Exception:
            mois = None

    if mois:
        display_month_text = f"Selected period : {mois}"
    else:
        display_month_text = "Complete view : All dates"

    # 🔎 Filtrer selon type, discipline, et mois
    def filtrer(type_selected):
        df = combined_df[combined_df['Type'] == type_selected]
        if selected_discipline != "ALL":
            df = df[df['Discipline'] == selected_discipline]
        if mois:
            df = df[df['Month'] == mois]
        return df

    demob_df = filtrer(type_demob)
    mob_df = filtrer(type_mob)

    # 🔀 DEMOB : tri dynamique
    if triggered_id == 'sort-button':
        sort_order = False if current_sort == 'asc' else True
        new_sort = 'desc' if current_sort == 'asc' else 'asc'
    else:
        sort_order = True if current_sort == 'asc' else False
        new_sort = current_sort

    demob_df_sorted = demob_df.sort_values(by='Original Demob Date', ascending=sort_order)

    rows_demob = [
        html.Tr([
            html.Td(row["Candidate'a name"], style={'border': '1px solid #ccc'}),
            html.Td(row["Original Demob Date"].strftime('%d %b %Y'), style={'border': '1px solid #ccc'}),
            html.Td(row["JOB TITLE per manning"], style={'border': '1px solid #ccc'})
        ])
        for _, row in demob_df_sorted.dropna(subset=["Candidate'a name", "Original Demob Date", "JOB TITLE per manning"]).iterrows()
    ] or [html.Tr(html.Td("None"))]

    # 🔀 MOB : tri dynamique
    if triggered_id == 'sort-button2':
        sort_order2 = False if current_sort2 == 'asc' else True
        new_sort2 = 'desc' if current_sort2 == 'asc' else 'asc'
    else:
        sort_order2 = True if current_sort2 == 'asc' else False
        new_sort2 = current_sort2

    mob_df_sorted = mob_df.sort_values(by='Date', ascending=sort_order2)

    rows_mob = [
        html.Tr([
            html.Td(row["Date"].strftime('%d %b %Y'), style={'border': '1px solid #ccc'}),
            html.Td(row["JOB TITLE per manning"], style={'border': '1px solid #ccc'})
        ])
        for _, row in mob_df_sorted.dropna(subset=["Date", "JOB TITLE per manning"]).iterrows()
    ] or [html.Tr(html.Td("None"))]

    return rows_demob, rows_mob, new_sort, new_sort2, display_month_text


if __name__ == "__main__":
    app.run_server(debug=True)
