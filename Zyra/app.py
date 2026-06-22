import streamlit as st
from groq import Groq
import json
import pandas as pd
import plotly.express as px

# ================= CONFIG =================

client = Groq(api_key="")

st.set_page_config(page_title="Zyra Ai", layout="wide")
st.title("🧠 ZYRA")
st.subheader("FMCG | Tier 2/3 India")

region = st.selectbox(
    "Select Target Region",
    ["Tier 2 Uttar Pradesh", "Punjab Rural", "Tamil Nadu Tier 3"]
)

# ================= SIMULATION FUNCTION =================

def run_full_simulation(script_text):

    completion = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {
                "role": "system",
                "content": "You are an enterprise cultural risk auditor and market simulation engine. Return valid JSON only."
            },
            {
                "role": "user",
                "content": f"""
You are a cultural risk auditor and market compliance evaluator.

Region: {region}

Ad Script:
{script_text}

Analyze deeply for tone aggression, generational conflict, tradition disrespect, social embarrassment framing, and class shaming.

Return EXACTLY this JSON:

{{
  "personas": [
    {{
      "name": "string",
      "age": number,
      "occupation": "string",
      "sentiment_score": number,
      "purchase_intent": number,
      "attention_score_percent": number
    }}
  ],
  "sentiment_breakdown": {{
    "positive_percent": number,
    "neutral_percent": number,
    "negative_percent": number
  }},
  "attention_analysis": {{
    "general_attention_score_percent": number,
    "attention_threshold_crossed": true
  }},
  "backlash_probability_percent": number,
  "risk_level": "Low | Medium | High",
  "script_sensitivity_analysis": [
    {{
      "problematic_line": "exact line",
      "issue_type": "string",
      "risk_impact_percent": number
    }}
  ],
  "kpi_estimates": {{
    "predicted_ctr_percent": number,
    "estimated_roas": number
  }},
  "executive_recommendation": {{
    "recommendation": "Safe to Launch | Launch with Modifications | Do Not Launch",
    "rationale": "string"
  }}
}}

Return JSON only.
"""
            }
        ],
        temperature=0.1
    )

    raw = completion.choices[0].message.content
    start = raw.find("{")
    end = raw.rfind("}") + 1
    cleaned = raw[start:end]

    return json.loads(cleaned)

# ================= SCORING =================

def calculate_success_score(result):
    backlash = result.get("backlash_probability_percent", 0)
    attention = result.get("attention_analysis", {}).get("general_attention_score_percent", 0)
    positive = result.get("sentiment_breakdown", {}).get("positive_percent", 0)
    roas = result.get("kpi_estimates", {}).get("estimated_roas", 0)

    score = (
        (100 - backlash) * 0.3 +
        attention * 0.25 +
        positive * 0.25 +
        min(roas * 20, 100) * 0.2
    )

    return round(score, 2)

def calculate_confidence(result):
    positive = result.get("sentiment_breakdown", {}).get("positive_percent", 0)
    backlash = result.get("backlash_probability_percent", 0)
    attention = result.get("attention_analysis", {}).get("general_attention_score_percent", 0)

    confidence = (
        (100 - backlash) * 0.4 +
        attention * 0.3 +
        positive * 0.3
    )

    return round(confidence, 2)

# ================= UI =================

script_input = st.text_area("Paste Script Here", height=200)

if st.button("Run Full Analysis"):

    if not script_input.strip():
        st.warning("Please enter a script.")
    else:
        with st.spinner("Running Enterprise Simulation..."):

            try:
                data = run_full_simulation(script_input)

                st.success("Analysis Complete ✅")

                # ================= SUCCESS =================

                success = calculate_success_score(data)
                st.header("🏆 Overall Success Potential")
                st.metric("Success Score", f"{success}/100")

                if success > 75:
                    st.success("Strong commercial viability.")
                elif success > 50:
                    st.warning("Promising but can be optimized.")
                else:
                    st.error("High risk of underperformance.")

                # ================= ATTENTION =================

                st.header("🎯 Attention Analysis")

                attention = data.get("attention_analysis", {}).get("general_attention_score_percent", 0)
                st.metric("General Attention Score", f"{attention}%")
                st.progress(attention / 100)

                # ================= SENTIMENT CHART =================

                st.header("📊 Audience Reaction Overview")

                sb = data.get("sentiment_breakdown", {})
                sentiment_df = pd.DataFrame({
                    "Sentiment": ["Positive", "Neutral", "Negative"],
                    "Percent": [
                        sb.get("positive_percent", 0),
                        sb.get("neutral_percent", 0),
                        sb.get("negative_percent", 0)
                    ]
                })

                fig = px.pie(sentiment_df, names="Sentiment", values="Percent", hole=0.5)
                st.plotly_chart(fig, use_container_width=True)

                # ================= PERSONAS =================

                st.header("👥 Persona Simulation")

                personas = data.get("personas", [])

                persona_df = pd.DataFrame(personas)

                if not persona_df.empty:
                    st.dataframe(persona_df)

                    fig2 = px.bar(
                        persona_df,
                        x="name",
                        y="attention_score_percent",
                        title="Persona Attention Distribution"
                    )
                    st.plotly_chart(fig2, use_container_width=True)

                # ================= PERFORMANCE =================

                st.header("📈 Performance Metrics")

                kpi = data.get("kpi_estimates", {})

                col1, col2, col3 = st.columns(3)

                col1.metric("Backlash %", f"{data.get('backlash_probability_percent',0)}%")
                col2.metric("CTR %", f"{kpi.get('predicted_ctr_percent',0)}%")
                col3.metric("ROAS", kpi.get("estimated_roas", 0))

                # ================= RISK =================

                st.header("🚨 Creative Risk & Improvement Insights")

                issues = data.get("script_sensitivity_analysis", [])

                if isinstance(issues, str):
                    st.info(issues)

                elif isinstance(issues, list) and issues:
                    valid = [i for i in issues if isinstance(i, dict)]

                    for issue in sorted(valid, key=lambda x: x.get("risk_impact_percent",0), reverse=True):

                        impact = issue.get("risk_impact_percent", 0)

                        if impact > 60:
                            st.error(f"HIGH RISK — {impact}% impact")
                        elif impact > 30:
                            st.warning(f"MODERATE RISK — {impact}% impact")
                        else:
                            st.info(f"LOW RISK — {impact}% impact")

                        st.write(f"Line: \"{issue.get('problematic_line','')}\"")
                        st.caption(f"Issue Type: {issue.get('issue_type','')}")
                        st.markdown("---")

                else:
                    st.success("No major line-level risk detected.")

                # ================= CONFIDENCE =================

                st.header("📡 Prediction Confidence")

                confidence = calculate_confidence(data)
                st.metric("Confidence Score", f"{confidence}%")
                st.progress(confidence / 100)

                # ================= DECISION =================

                st.header("🧾 Executive Recommendation")

                decision = data.get("executive_recommendation", {})

                if isinstance(decision, dict):
                    st.subheader(decision.get("recommendation", "Pending"))
                    st.write(decision.get("rationale", ""))
                else:
                    st.write(decision)

            except Exception as e:
                st.error("Something went wrong.")
                st.write(e)
