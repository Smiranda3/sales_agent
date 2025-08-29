from langchain_tavily import TavilySearch
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
import streamlit as st
from dotenv import load_dotenv
import json
import datetime
import time
from fpdf import FPDF
import io

load_dotenv()

# Initialize session state for alerts and history
if 'report_history' not in st.session_state:
    st.session_state.report_history = []
if 'alerts' not in st.session_state:
    st.session_state.alerts = []

# Model
llm = ChatGroq(model="openai/gpt-oss-20b")  
# Tool
search_tool = TavilySearch(topic="general", max_results=4)

# Define alert keywords at module level
ALERT_KEYWORDS = ["acquisition", "merger", "funding", "partnership", "expansion", "new product", "leadership change"]

def enhanced_search(company_name, company_url, product_name):
    """Perform multiple targeted searches for comprehensive insights"""
    search_queries = [
        f"{company_name} recent news business strategy",
        f'"{company_name}" competitors partnerships {product_name}',
        f'"{company_name}" funding acquisition merger 2024 2025',
        f'"{company_name}" leadership team executives',
        f'{product_name} market trends competitive landscape'
    ]
    
    all_results = []
    
    for query in search_queries:
        try:
            print(f"Searching for: {query}")
            results = search_tool.invoke(query)
            if results:
                all_results.extend(results if isinstance(results, list) else [results])
            time.sleep(0.5)  # Rate limiting
        except Exception as e:
            print(f"Search query failed: {query} - Error: {str(e)}")
            st.warning(f"Search query failed: {query[:50]}... Error: {str(e)}")
            continue
    
    print(f"Total results found: {len(all_results)}")
    return all_results

def check_for_alerts(search_results, company_name):
    """Check search results for alert-worthy information"""
    alerts = []
    
    for result in search_results:
        content = str(result).lower()
        for keyword in ALERT_KEYWORDS:  # Fixed: Use module-level variable
            if keyword in content:
                alerts.append({
                    'company': company_name,
                    'keyword': keyword,
                    'timestamp': datetime.datetime.now(),
                    'content': str(result)[:200] + "..."
                })
    
    return alerts

def generate_enhanced_insights(company_name, product_name, company_url, company_competitors, industry_context=""):
    """Generate comprehensive sales insights"""
    
    try:
        # Perform enhanced search
        search_results = enhanced_search(company_name, company_url, product_name)
        
        # Check for alerts
        new_alerts = check_for_alerts(search_results, company_name)
        st.session_state.alerts.extend(new_alerts)
        
        if not search_results:
            return "❌ **No search results found. Please check the company name and try again.**"
        
        # Prepare search results for the prompt
        search_content = ""
        for i, result in enumerate(search_results[:10]):  # Limit to first 10 results
            search_content += f"Result {i+1}: {str(result)}\n\n"
        
        messages = [
            SystemMessage(content="""You are an expert B2B sales intelligence analyst with deep expertise in:
        - Competitive intelligence and market analysis
        - Strategic business assessment
        - Decision-maker identification and influence mapping
        - Sales opportunity assessment and timing
        
        Provide actionable insights that directly support sales strategy and engagement planning.
        Focus on concrete, specific information that can inform sales conversations and approach."""),

            HumanMessage(content=f"""
            Based on the following search results, provide a comprehensive sales intelligence report.
            
            Search Results:
            {search_content}
            
            Company: {company_name}
            Product: {product_name}
            Competitors: {company_competitors}
            Company URL: {company_url}
            
            Please structure your response as follows:
            
            ## Executive Summary
            Provide a 2-3 sentence strategic overview of this sales opportunity.
            
            ## Company Strategic Profile
            - Current business strategy and priorities
            - Recent strategic initiatives, funding, or major changes
            - Growth areas and expansion plans
            - Technology stack and digital transformation initiatives
            
            ## Competitive Landscape Analysis
            - Current vendors and technology partners
            - Competitive threats and market positioning
            - Partnership opportunities
            - Switching costs and vendor lock-in considerations
            
            ## Key Stakeholders & Decision Makers
            - Primary decision makers and their backgrounds
            - Influence network and reporting structure
            - Past experience with similar solutions
            - Preferred communication styles and channels
            
            ## Sales Opportunity Assessment
            - Market timing and urgency indicators
            - Budget and procurement cycle insights
            - Potential pain points and value propositions
            - Recommended engagement strategy and talking points
            - Risk factors and potential objections
            
            ## Next Steps & Action Items
            - Immediate research follow-ups needed
            - Recommended outreach sequence
            - Key questions to ask in initial conversations
            - Resources and case studies to prepare
            
            **FORMAT:** Use clear markdown formatting with proper headings, bullet points, and emphasis for key insights.
            **TONE:** Professional, analytical, and action-oriented.
            **LENGTH:** Comprehensive but scannable - aim for 350-500 words.
            """)
        ]

        print("Sending request to LLM...")
        model_response = llm.invoke(messages)
        print(f"Model Response received: {len(model_response.content)} characters")
        
        # Save to history
        report_entry = {
            'company': company_name,
            'product': product_name,
            'content': model_response.content,
            'timestamp': datetime.datetime.now()
        }
        st.session_state.report_history.append(report_entry)
        
        return model_response.content
        
    except Exception as e:
        error_msg = f"Error generating insights: {str(e)}"
        print(error_msg)
        st.error(error_msg)
        return f"❌ **Error generating report:** {str(e)}"

def create_pdf(report_content, company_name):
    """Create PDF from report content"""
    try:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font('Arial', 'B', 16)
        pdf.cell(0, 10, f'Sales Insights Report - {company_name}', 0, 1, 'C')
        pdf.ln(10)
        
        pdf.set_font('Arial', '', 10)
        
        # Handle markdown-style content
        lines = report_content.split('\n')
        for line in lines:
            if line.strip():
                # Handle special characters
                safe_line = line.encode('latin-1', 'replace').decode('latin-1')
                # Wrap long lines
                if len(safe_line) > 90:
                    words = safe_line.split(' ')
                    current_line = ""
                    for word in words:
                        if len(current_line + word) < 90:
                            current_line += word + " "
                        else:
                            if current_line:
                                pdf.cell(0, 5, current_line.strip(), 0, 1)
                            current_line = word + " "
                    if current_line:
                        pdf.cell(0, 5, current_line.strip(), 0, 1)
                else:
                    pdf.cell(0, 5, safe_line, 0, 1)
            else:
                pdf.ln(3)
        
        pdf_output = io.BytesIO()
        pdf_string = pdf.output(dest='S').encode('latin-1')
        pdf_output.write(pdf_string)
        pdf_output.seek(0)
        return pdf_output.getvalue()
    except Exception as e:
        st.error(f"Error creating PDF: {str(e)}")
        return None

# ============= UI ==============
st.title("🎯 Sales Insights Agent")
st.subheader("Generate a comprehensive sales insights report")
st.divider()

# Sidebar for configuration and alerts
with st.sidebar:
    st.header("⚙️ Advanced features")
    
    # Alert system
    st.subheader("🚨 Recent Alerts")
    if st.session_state.alerts:
        recent_alerts = sorted(st.session_state.alerts, key=lambda x: x['timestamp'], reverse=True)[:5]
        for alert in recent_alerts:
            st.warning(f"**{alert['company']}**: {alert['keyword']} detected")
            st.caption(f"{alert['timestamp'].strftime('%Y-%m-%d %H:%M')}")
    else:
        st.info("No alerts yet")
    
    if st.button("Clear Alerts"):
        st.session_state.alerts = []
        st.rerun()
    
    st.divider()
    
    # Report history
    st.subheader("📚 Report History")
    if st.session_state.report_history:
        for i, report in enumerate(reversed(st.session_state.report_history[-5:])):
            if st.button(f"{report['company']} - {report['timestamp'].strftime('%m/%d %H:%M')}", key=f"history_{i}"):
                st.session_state.selected_historical_report = report
    else:
        st.info("No reports generated yet")

# Input fields
col1, col2 = st.columns(2)
with col1:
    company_name = st.text_input("Company Name", placeholder="e.g., Microsoft, Apple, Tesla")
    company_url = st.text_input("Company URL", placeholder="e.g., microsoft.com")

with col2:
    product_name = st.text_input("Product Name", placeholder="e.g., Office 365, CRM Software")
    company_competitors = st.text_input("Company Competitors", placeholder="e.g., Salesforce, HubSpot")

# Generate report
if st.button("Generate Report", type="primary"):
    if company_name and company_url:
        with st.spinner("🔍 Searching for company information..."):
            st.info(f"Analyzing {company_name}...")
            
            result = generate_enhanced_insights(company_name, product_name, company_url, company_competitors)
            
            st.divider()
            st.markdown("## 📊 Sales Insights Report")
            st.markdown(result)
            
            # Download options
            col1, col2 = st.columns(2)
            
            with col1:
                st.download_button(
                    "📄 Download as Text",
                    result,
                    file_name=f"sales_report_{company_name.replace(' ', '_')}.txt",
                    mime="text/plain"
                )
            
            with col2:
                pdf_data = create_pdf(result, company_name)
                if pdf_data:
                    st.download_button(
                        "📑 Download as PDF",
                        pdf_data,
                        file_name=f"sales_report_{company_name.replace(' ', '_')}.pdf",
                        mime="application/pdf"
                    )
    else:
        st.warning("⚠️ Please enter both company name and URL to generate a report.")

# Display historical report if selected
if 'selected_historical_report' in st.session_state:
    st.divider()
    st.markdown("## 📚 Historical Report")
    historical = st.session_state.selected_historical_report
    st.markdown(f"**Company:** {historical['company']}")
    st.markdown(f"**Generated:** {historical['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")
    st.markdown(historical['content'])
    
    if st.button("Clear Historical View"):
        del st.session_state.selected_historical_report
        st.rerun()


