
import os
import pandas as pd
from typing import List
import google.generativeai as genai

def generate_efficiency_tips(df: pd.DataFrame, gemini_api_key: str = None) -> List[str]:
    """Generate personalized efficiency tips using Gemini 2.5 Flash model."""
    if not gemini_api_key:
        return ["AI insights unavailable (Gemini API key not configured)"]
    try:
        genai.configure(api_key=gemini_api_key)
        model = genai.GenerativeModel('models/gemini-2.5-flash')
        usage_summary = f"Total: {df['usage_kWh'].sum():.2f} kWh, Average: {df['usage_kWh'].mean():.2f} kWh/day, Peak: {df['usage_kWh'].max():.2f} kWh"
        prompt = (
            f"You are an energy efficiency expert. Based on this usage summary: {usage_summary}, "
            "give 2-3 personalized tips to reduce electricity consumption."
        )
        response = model.generate_content(prompt)
        content = response.text.strip()
        tips = [tip for tip in content.split('\n') if tip.strip()]
        return tips
    except Exception as e:
        return [f"AI insights unavailable (error generating tips: {e})"]

def get_gemini_insight(question: str, context: str = "", gemini_api_key: str = None) -> str:
    """Get a Gemini-powered answer to a custom question, with context (CSV or summary)."""
    if not gemini_api_key:
        return "AI insights unavailable (Gemini API key not configured)"
    try:
        genai.configure(api_key=gemini_api_key)
        model = genai.GenerativeModel('models/gemini-2.5-flash')
        prompt = f"You are an energy analytics expert. Context:\n{context}\n\nQuestion: {question}\nAnswer as clearly and concisely as possible."
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"AI insights unavailable (error: {e})"
