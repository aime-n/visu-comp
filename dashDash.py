import pandas as pd
import plotly.express as px
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import dash_bootstrap_components as dbc
from plotly.subplots import make_subplots
import numpy as np

df_source = pd.read_csv('https://github.com/helber-usp/data-storage/blob/main/Environment_Temperature_change_E_All_Data_NOFLAG.csv?raw=true', encoding = 'ISO-8859-1')
df_paises = df_source[df_source['Element'] == 'Temperature change']
df_paises.drop(columns=['Area Code', 'Months Code', 'Element Code', 'Element', 'Unit'], inplace=True)
df_paises.reset_index(inplace=True)
df_paises.drop(columns='index', inplace=True)
df_melted = pd.melt(df_paises, id_vars=['Area', 'Months'], var_name='Year', value_name='Temperatura')
df_melted['Year'] = df_melted['Year'].str.replace('Y', '')

def get_months(df, country=False):
    if country!=False:
        df = df[df['Area'] == country]
    months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'September', 'October', 'November', 'December']
    df = df[df['Months'].isin(months)]
    df['YMonth'] = pd.to_datetime(df['Year']+ '-' + df['Months'], format='%Y-%B').dt.strftime('%Y-%m')
    return df
df = get_months(df_melted)
df = df.sort_values('YMonth')
df['NumericMonth'] = pd.to_datetime(df['YMonth']).sub(pd.to_datetime(df['YMonth'].min())).dt.days // 30
unique_years = df['Year'].unique()


app = dash.Dash(__name__, external_stylesheets=[dbc.themes.DARKLY])
app.layout = html.Div([
    html.H1("Trabalho de Visualização Computacional: Aquecimento Global", style={'textAlign': 'center', 'color': 'white', "fontSize":40}),
    html.H2("Cícero Coimbra Fonseca - 12624912, Helber Martins de Moraes - 10260181, Aimê - 11882429", style={'textAlign': 'center', "fontSize":30}),
    html.Label('Selecione regiões para analisar:'),
    dcc.Dropdown(
        id='area-dropdown',
        options=[{'label': area, 'value': area} for area in df['Area'].unique()],
        value=['World'],
        multi=True
    ),
    html.Label('Selecione um intervalo de tempo para analisar:'),
    dcc.RangeSlider(
        id='date-range-slider',
        marks={i: str(year) for i, year in enumerate(unique_years) if i % 5 == 0},  # Show marks for every 5 years
        min=0,
        max=len(unique_years) - 1,
        step=1,
        value=[40, len(unique_years) - 1]
    ),
    dcc.Graph(id='temperature-line-chart-global'),
    dcc.Graph(id='temperature-line-chart-seasonal'),
    dcc.Graph(id='temperature-change-chart'),
    html.P("08/2023", style={'textAlign': 'center', 'fontSize': 12})
])
@app.callback(
    Output('temperature-line-chart-global', 'figure'),
    [Input('area-dropdown', 'value'),
     Input('date-range-slider', 'value')]
)
def update_global_chart(selected_areas, selected_years):
    filtered_df = df[(df['Area'].isin(selected_areas)) & (df['Year'] >= unique_years[selected_years[0]]) & (df['Year'] <= unique_years[selected_years[1]])]
    fig_global = px.line(filtered_df, x='YMonth', y='Temperatura', color='Area', labels={'Temperatura': 'Temperatura (°C)'})
    fig_global.update_layout(template='plotly_dark')
    fig_global.update_layout(title='Gráfico de Série Temporal para mudança de temperatura média nas regiões selecionadas',
                             xaxis_title='Tempo (Ano-Mês)',
                             yaxis_title='Temperatura (°C)')

    return fig_global
@app.callback(
    Output('temperature-line-chart-seasonal', 'figure'),
    [Input('area-dropdown', 'value'),
     Input('date-range-slider', 'value')]
)
def update_seasonal_chart(selected_areas, selected_years):
    filtered_df = df[(df['Area'].isin(selected_areas)) & (df['Year'] >= unique_years[selected_years[0]]) & (df['Year'] <= unique_years[selected_years[1]])]
    filtered_df['Decade'] = ((filtered_df['Year'].apply(int) // 10) * 10).apply(str) + "'s"
    filtered_df = filtered_df.groupby(['Decade', 'Area', 'Months'])['Temperatura'].mean().reset_index()

    month_order = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
    filtered_df['Months'] = pd.Categorical(filtered_df['Months'], categories=month_order, ordered=True)
    filtered_df = filtered_df.sort_values('Months')

    num_rows = (len(selected_areas) + 2) // 3
    num_cols = min(len(selected_areas), 3)
    subplot_height = 600 // num_rows
    fig_seasonal = make_subplots(rows=num_rows, cols=num_cols, subplot_titles=selected_areas, row_heights=[subplot_height]*num_rows)
    for i, area in enumerate(selected_areas):
        for j, decade in enumerate(filtered_df[filtered_df['Area'] == area]['Decade'].unique()):
            data = filtered_df[(filtered_df['Area'] == area) & (filtered_df['Decade'] == decade)]
            row_index = (i // 3) + 1
            col_index = (i % 3) + 1
            color_scale = px.colors.sequential.Plasma
            color_index = int((int(decade[:4]) - int(unique_years[selected_years[0]])) / (int(unique_years[selected_years[1]]) - int(unique_years[selected_years[0]])) * (len(color_scale) - 1))
            color_index = max(0, min(color_index, len(color_scale) - 1))
            color = color_scale[color_index]
            fig_seasonal.add_trace(
                px.line(data, x='Months', y='Temperatura', color='Decade', color_discrete_sequence=[color]).update_traces(name=str(decade), opacity=0.4).data[0],
                row=row_index, col=col_index
            )
            fig_seasonal.add_trace(
                px.scatter(x=[None], y=[None]).update_traces(name=str(decade)).data[0],
                row=row_index, col=col_index
            )
    fig_seasonal.update_layout(template='plotly_dark')
    fig_seasonal.update_layout(title_text='Gráfico de sazonalidade para mudança de temperatura média nas regiões selecionadas',
                               xaxis_title='Mês',
                               yaxis_title='Temperatura (°C)')
    return fig_seasonal

@app.callback(
    Output('temperature-change-chart', 'figure'),
    [Input('area-dropdown', 'value'),
     Input('date-range-slider', 'value')]
)
def update_change_chart(selected_areas, selected_years):
    change_df = df[(df['Year'] >= unique_years[selected_years[0]]) & (df['Year'] <= unique_years[selected_years[1]])]
    change_df = change_df.dropna()
    change_df = change_df.groupby(['Year', 'Area'])['Temperatura'].mean().reset_index()
    change_df['Variação de Temperatura'] = change_df['Temperatura'].abs()
    change_df['Natureza da Variação'] = np.sign(change_df['Temperatura']).map({1.0: 'Positive', -1.0: 'Negative', 0.0: 'Zero'})

    fig_change = px.scatter(change_df,
                            x='Area',
                            y='Variação de Temperatura',
                            size='Variação de Temperatura',
                            color='Natureza da Variação',
                            hover_name='Area',
                            animation_frame='Year',
                            title='Variação de Temperatura por País',
                            labels={'Variação de Temperatura': 'Variação Absoluta'},
                            color_discrete_map={'Positive': 'red', 'Negative': 'blue'},
                            size_max=30
                            )
    size_to_variation_mapping = {
    'Pequena': '0-0.5°C',
    'Média': '0.5-1.5°C',
    'Grande': '1.5-3+°C'
    }

    # Ajusta a posição inicial das anotações e o espaçamento entre elas
    start_y_position = 0.6  # Ajuste esse valor conforme necessário
    spacing = 0.1  # Espaçamento entre as anotações

    # Adiciona anotações para a legenda de tamanho
    for i, (size_label, temp_range) in enumerate(size_to_variation_mapping.items()):
        fig_change.add_annotation(
            xref="paper", yref="paper",
            x=1.02, y=start_y_position - (i * spacing),
            text=f"{size_label}: {temp_range}",
            showarrow=False,
            xanchor="left",
            yanchor="middle",
            align="left"
        )
  

    fig_change.update_layout(margin=dict(l=20, r=20, t=30, b=210))
    fig_change['layout']['updatemenus'][0]['pad']=dict(r= 10, t= 130)
    fig_change['layout']['sliders'][0]['pad']=dict(r= 10, t= 130)
    fig_change.update_layout(template='plotly_dark')

    fig_change.update_layout(title='Variação de Temperatura Média Anual Por País',
                             xaxis_title='País',
                             xaxis=dict(showticklabels=False),
                             yaxis=dict(range=[0, 3.5]))

    return fig_change

if __name__ == '__main__':
    app.run_server(debug=False)