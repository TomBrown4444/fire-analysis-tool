"""
UI utility functions for the Fire Investigation Tool.
Provides helper functions for the user interface components.
"""
import streamlit as st
import streamlit.components.v1 as components

def setup_page_config():
    """Set up the Streamlit page configuration."""
    st.set_page_config(
        page_title="Fire Investigation Tool",
        page_icon="🔥",
        layout="wide",
        initial_sidebar_state="expanded"
    )

def create_custom_sidebar_js():
    """
    Create JavaScript for toggling the sidebar with cluster information.
    Returns the HTML/JS code to include in the page.
    """
    # Add JavaScript for toggling the sidebar
    toggle_js = """
    <script>
    function toggleSidebar() {
        const sidebar = document.querySelector('.cluster-sidebar');
        const button = document.querySelector('.sidebar-toggle');
        sidebar.classList.toggle('hidden');
        button.classList.toggle('hidden');
        if (sidebar.classList.contains('hidden')) {
            button.innerHTML = '◀ Show Cluster Table';
        } else {
            button.innerHTML = '▶ Hide';
        }
    }
    </script>
    """
    
    # Create HTML for the sidebar - use safe access to session state
    sidebar_visible = st.session_state.get('sidebar_visible', True)
    sidebar_class = "" if sidebar_visible else "hidden"
    button_class = "sidebar-toggle" if sidebar_visible else "sidebar-toggle hidden"
    button_text = "▶ Hide" if sidebar_visible else "◀ Show Cluster Table"
    
    sidebar_html = f"""
    <div class="cluster-sidebar {sidebar_class}" id="clusterSidebar">
        <h3>Cluster Summary</h3>
        <div id="sidebar-content">
            <!-- The table content will be inserted here by Streamlit -->
        </div>
    </div>
    <button onclick="toggleSidebar()" class="{button_class}">{button_text}</button>
    {toggle_js}
    """
    
    return sidebar_html

def move_content_to_sidebar_js():
    """
    Create JavaScript to move content to the sidebar container.
    Returns the JS code to include in the page.
    """
    sidebar_js = """
    <script>
    // Function to move content to sidebar
    function moveSidebarContent() {
        const content = document.getElementById('hidden-sidebar-content');
        const sidebar = document.getElementById('sidebar-content');
        if (content && sidebar) {
            sidebar.innerHTML = content.innerHTML;
            content.style.display = 'none';
        }
    }
    
    // Execute after page is loaded
    if (document.readyState === 'complete') {
        moveSidebarContent();
    } else {
        window.addEventListener('load', moveSidebarContent);
    }
    </script>
    """
    return sidebar_js

def custom_css():
    """Return custom CSS for the application."""
    return """
    <style>
    .stButton button { 
        font-size: 20px; 
        padding: 15px; 
    }
    
    .cluster-sidebar {
        position: fixed;
        top: 60px;
        right: 0;
        width: 300px;
        height: calc(100vh - 60px);
        background-color: #f0f2f6;
        z-index: 1000;
        overflow-y: auto;
        transition: transform 0.3s ease;
        padding: 15px;
        box-shadow: -2px 0 5px rgba(0,0,0,0.1);
    }
    
    .cluster-sidebar.hidden {
        transform: translateX(310px);
    }
    
    .sidebar-toggle {
        position: fixed;
        top: 70px;
        right: 310px;
        z-index: 1001;
        background-color: #4CAF50;
        color: white;
        border: none;
        padding: 8px 16px;
        cursor: pointer;
        border-radius: 4px 0 0 4px;
        transition: right 0.3s ease;
    }
    
    .sidebar-toggle.hidden {
        right: 0;
    }
    </style>
    """