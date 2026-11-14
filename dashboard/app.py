import json
import streamlit as st
import plotly.graph_objects as go
from agents.orchestrator import run
from agents.reporter import markdown
from agents.schemas import BalanceGoal

st.title('Ragent balance analysis')
st.caption('Mock simulation is clearly identified until the simulator is installed.')
config_text=st.text_area('Configuration JSON', open('configs/baseline.json').read(), height=180)
goal_text=st.text_input('Balancing goal', 'Reduce sniper defensive advantage with minimal changes')
constraints_text=st.text_area('Constraints JSON', json.dumps({'bounds':{'weapons.sniper.damage':[0,200], 'abilities.smoke.duration':[0,60]}}, indent=2), height=160)
matches=st.number_input('Match budget', min_value=9, value=100); iterations=st.number_input('Proposal rounds', min_value=1, value=2)
if st.button('Run analysis'):
    try:
        with st.spinner('Running experiments...'):
            report=run(json.loads(config_text), BalanceGoal(goal=goal_text, constraints=json.loads(constraints_text), matches=matches, iterations=iterations))
        st.session_state['report']=report.model_dump()
    except Exception as exc: st.error(str(exc))
if 'report' in st.session_state:
    r=st.session_state['report']; st.info('Data source: '+r['mode'])
    if r['baseline']:
        names=['Baseline']+[c['proposal']['name'] for c in r['candidates'] if 'metrics' in c]
        rates=[r['baseline']['attacker_win_rate']]+[c['metrics']['attacker_win_rate'] for c in r['candidates'] if 'metrics' in c]
        st.plotly_chart(go.Figure(go.Bar(x=names,y=rates)), use_container_width=True)
    st.subheader('Candidate comparison'); st.json(r['candidates'])
    st.subheader('Proposal rationales')
    for c in r['candidates']: st.write(c['proposal']['name']+': '+c['proposal']['rationale'])
    st.subheader('QA findings'); st.json(r['findings'])
    st.subheader('Recommended JSON diff'); st.json(r['recommendation']['proposal']['changes'] if r['recommendation'] else [])
    st.download_button('Download developer report', markdown(r), file_name='agent_report.md')
