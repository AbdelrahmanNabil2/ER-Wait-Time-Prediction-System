import streamlit as st
import subprocess
import json
import pandas as pd
from datetime import datetime
import time
import plotly.graph_objects as go
import plotly.express as px

st.set_page_config(
    page_title="Kubernetes Dashboard",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        color: #326CE5;
        text-align: center;
        margin-bottom: 2rem;
    }
    .status-healthy {
        background-color: #d4edda;
        padding: 0.5rem;
        border-radius: 0.3rem;
        color: #155724;
        font-weight: bold;
    }
    .status-unhealthy {
        background-color: #f8d7da;
        padding: 0.5rem;
        border-radius: 0.3rem;
        color: #721c24;
        font-weight: bold;
    }
    .status-warning {
        background-color: #fff3cd;
        padding: 0.5rem;
        border-radius: 0.3rem;
        color: #856404;
        font-weight: bold;
    }
    .metric-box {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 0.5rem;
        color: white;
        text-align: center;
    }
    </style>
""", unsafe_allow_html=True)

def run_kubectl_command(command):
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            return result.stdout, None
        else:
            return None, result.stderr
    except subprocess.TimeoutExpired:
        return None, "Command timeout"
    except Exception as e:
        return None, str(e)

def check_cluster_info():
    output, error = run_kubectl_command("kubectl cluster-info")
    if error:
        return None, error
    return output, None

def get_pods_status():
    output, error = run_kubectl_command("kubectl get pods -o json")
    if error:
        return None, error
    try:
        data = json.loads(output)
        pods = []
        for item in data.get('items', []):
            pod = {
                'name': item['metadata']['name'],
                'status': item['status']['phase'],
                'ready': sum(1 for c in item['status'].get('containerStatuses', []) if c.get('ready', False)),
                'total_containers': len(item['status'].get('containerStatuses', [])),
                'restarts': sum(c.get('restartCount', 0) for c in item['status'].get('containerStatuses', [])),
                'age': item['metadata'].get('creationTimestamp', ''),
                'node': item['spec'].get('nodeName', 'N/A')
            }
            pods.append(pod)
        return pods, None
    except Exception as e:
        return None, str(e)

def get_services_status():
    output, error = run_kubectl_command("kubectl get services -o json")
    if error:
        return None, error
    try:
        data = json.loads(output)
        services = []
        for item in data.get('items', []):
            service = {
                'name': item['metadata']['name'],
                'type': item['spec']['type'],
                'cluster_ip': item['spec'].get('clusterIP', 'N/A'),
                'external_ip': item['status'].get('loadBalancer', {}).get('ingress', [{}])[0].get('ip', 'localhost'),
                'ports': ', '.join([f"{p.get('port', 'N/A')}/{p.get('protocol', 'TCP')}" for p in item['spec'].get('ports', [])])
            }
            services.append(service)
        return services, None
    except Exception as e:
        return None, str(e)

def get_deployments_status():
    output, error = run_kubectl_command("kubectl get deployments -o json")
    if error:
        return None, error
    try:
        data = json.loads(output)
        deployments = []
        for item in data.get('items', []):
            deployment = {
                'name': item['metadata']['name'],
                'ready': f"{item['status'].get('readyReplicas', 0)}/{item['spec'].get('replicas', 0)}",
                'up_to_date': item['status'].get('updatedReplicas', 0),
                'available': item['status'].get('availableReplicas', 0),
                'age': item['metadata'].get('creationTimestamp', '')
            }
            deployments.append(deployment)
        return deployments, None
    except Exception as e:
        return None, str(e)

def get_hpa_status():
    output, error = run_kubectl_command("kubectl get hpa -o json")
    if error:
        return None, error
    try:
        data = json.loads(output)
        hpas = []
        for item in data.get('items', []):
            current_replicas = item['status'].get('currentReplicas', 0)
            desired_replicas = item['status'].get('desiredReplicas', 0)
            if desired_replicas == 0 and current_replicas > 0:
                desired_replicas = current_replicas
            current_cpu = "N/A"
            target_cpu = "N/A"
            metrics = item['spec'].get('metrics', [])
            for metric in metrics:
                if metric.get('type') == 'Resource' and metric.get('resource', {}).get('name') == 'cpu':
                    target_cpu = metric.get('resource', {}).get('target', {}).get('averageUtilization', 'N/A')
                    if target_cpu != 'N/A':
                        target_cpu = f"{target_cpu}%"
            current_metrics = item['status'].get('currentMetrics', [])
            for metric in current_metrics:
                if metric.get('type') == 'Resource' and metric.get('resource', {}).get('name') == 'cpu':
                    current_val = metric.get('resource', {}).get('current', {}).get('averageUtilization')
                    if current_val is not None:
                        current_cpu = f"{current_val}%"
            hpa = {
                'name': item['metadata']['name'],
                'reference': f"{item['spec']['scaleTargetRef']['kind']}/{item['spec']['scaleTargetRef']['name']}",
                'min_pods': item['spec'].get('minReplicas', 1),
                'max_pods': item['spec'].get('maxReplicas', 10),
                'current_replicas': current_replicas,
                'desired_replicas': desired_replicas,
                'current_cpu': current_cpu,
                'target_cpu': target_cpu
            }
            hpas.append(hpa)
        return hpas, None
    except Exception as e:
        return None, str(e)

def get_pod_logs(pod_name, lines=50):
    output, error = run_kubectl_command(f"kubectl logs {pod_name} --tail={lines}")
    if error:
        return None, error
    return output, None

def get_nodes_status():
    output, error = run_kubectl_command("kubectl get nodes -o json")
    if error:
        return None, error
    try:
        data = json.loads(output)
        nodes = []
        for item in data.get('items', []):
            node = {
                'name': item['metadata']['name'],
                'status': 'Ready' if any(c['type'] == 'Ready' and c['status'] == 'True' for c in item['status'].get('conditions', [])) else 'NotReady',
                'roles': ', '.join(item['metadata'].get('labels', {}).get('kubernetes.io/role', 'worker').split(',')),
                'version': item['status']['nodeInfo']['kubeletVersion']
            }
            nodes.append(node)
        return nodes, None
    except Exception as e:
        return None, str(e)

def main():
    st.markdown('<div class="main-header">Kubernetes Monitoring Dashboard</div>', unsafe_allow_html=True)
    st.sidebar.header("Dashboard Controls")
    auto_refresh = st.sidebar.checkbox("Auto Refresh", value=False)
    refresh_interval = st.sidebar.slider("Refresh Interval (seconds)", 5, 60, 10)
    if st.sidebar.button("Refresh Now") or auto_refresh:
        st.rerun()
    cluster_info, error = check_cluster_info()
    if error:
        st.error(f"Cannot connect to Kubernetes cluster: {error}")
        st.info("Make sure kubectl is configured and the cluster is running")
        st.stop()
    st.success("Connected to Kubernetes cluster")
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["Overview", "Pods", "Services", "Deployments", "HPA", "Logs"])
    with tab1:
        st.subheader("Cluster Overview")
        pods, _ = get_pods_status()
        services, _ = get_services_status()
        deployments, _ = get_deployments_status()
        nodes, _ = get_nodes_status()
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            total_pods = len(pods) if pods else 0
            running_pods = sum(1 for p in pods if p['status'] == 'Running') if pods else 0
            st.metric("Total Pods", total_pods, delta=f"{running_pods} Running")
        with col2:
            total_services = len(services) if services else 0
            st.metric("Services", total_services)
        with col3:
            total_deployments = len(deployments) if deployments else 0
            st.metric("Deployments", total_deployments)
        with col4:
            total_nodes = len(nodes) if nodes else 0
            ready_nodes = sum(1 for n in nodes if n['status'] == 'Ready') if nodes else 0
            st.metric("Nodes", total_nodes, delta=f"{ready_nodes} Ready")
        st.markdown("---")
        with st.expander("Cluster Information", expanded=True):
            st.code(cluster_info, language="text")
        if nodes:
            st.subheader("Nodes Status")
            df_nodes = pd.DataFrame(nodes)
            st.dataframe(df_nodes, use_container_width=True, hide_index=True)
        if pods:
            st.subheader("Pod Status Distribution")
            status_counts = {}
            for pod in pods:
                status = pod['status']
                status_counts[status] = status_counts.get(status, 0) + 1
            fig = go.Figure(data=[go.Pie(labels=list(status_counts.keys()), values=list(status_counts.values()), hole=0.3)])
            fig.update_layout(title="Pod Status Distribution", height=400)
            st.plotly_chart(fig, use_container_width=True)
    with tab2:
        st.subheader("Pod Status")
        pods, error = get_pods_status()
        if error:
            st.error(f"Error fetching pods: {error}")
        elif pods:
            col1, col2 = st.columns(2)
            with col1:
                status_filter = st.multiselect("Filter by Status", options=list(set(p['status'] for p in pods)), default=list(set(p['status'] for p in pods)))
            filtered_pods = [p for p in pods if p['status'] in status_filter]
            for pod in filtered_pods:
                ready_status = f"{pod['ready']}/{pod['total_containers']}"
                status_class = "status-healthy" if pod['status'] == 'Running' and pod['ready'] == pod['total_containers'] else "status-warning" if pod['status'] == 'Running' else "status-unhealthy"
                with st.expander(f"{pod['name']} - {pod['status']}", expanded=False):
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.markdown(f"**Status:** <span class='{status_class}'>{pod['status']}</span>", unsafe_allow_html=True)
                    with col2:
                        st.write(f"**Ready:** {ready_status}")
                    with col3:
                        st.write(f"**Restarts:** {pod['restarts']}")
                    with col4:
                        st.write(f"**Node:** {pod['node']}")
        else:
            st.info("No pods found")
    with tab3:
        st.subheader("Services")
        services, error = get_services_status()
        if error:
            st.error(f"Error fetching services: {error}")
        elif services:
            df_services = pd.DataFrame(services)
            st.dataframe(df_services, use_container_width=True, hide_index=True)
        else:
            st.info("No services found")
    with tab4:
        st.subheader("Deployments")
        deployments, error = get_deployments_status()
        if error:
            st.error(f"Error fetching deployments: {error}")
        elif deployments:
            for deployment in deployments:
                with st.expander(f"{deployment['name']}", expanded=True):
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Ready Replicas", deployment['ready'])
                    with col2:
                        st.metric("Up-to-Date", deployment['up_to_date'])
                    with col3:
                        st.metric("Available", deployment['available'])
                    with col4:
                        st.write(f"**Age:** {deployment['age'][:10]}")
        else:
            st.info("No deployments found")
    with tab5:
        st.subheader("Horizontal Pod Autoscaler")
        hpas, error = get_hpa_status()
        if error:
            st.warning(f"HPA not available or error: {error}")
        elif hpas:
            for hpa in hpas:
                with st.expander(f"{hpa['name']}", expanded=True):
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Min Pods", hpa['min_pods'])
                    with col2:
                        st.metric("Current Replicas", hpa['current_replicas'])
                    with col3:
                        st.metric("Max Pods", hpa['max_pods'])
                    with col4:
                        st.metric("CPU", f"{hpa['current_cpu']} / {hpa['target_cpu']}")
                    st.write(f"**Target:** {hpa['reference']}")
                    st.write(f"**Desired Replicas:** {hpa['desired_replicas']}")
        else:
            st.info("No HPA configurations found")
    with tab6:
        st.subheader("Pod Logs")
        pods, _ = get_pods_status()
        if pods:
            pod_names = [p['name'] for p in pods]
            selected_pod = st.selectbox("Select Pod", pod_names)
            log_lines = st.slider("Number of lines", 10, 200, 50)
            if st.button("Fetch Logs"):
                with st.spinner("Fetching logs..."):
                    logs, error = get_pod_logs(selected_pod, log_lines)
                    if error:
                        st.error(f"Error fetching logs: {error}")
                    else:
                        st.code(logs, language="text")
        else:
            st.info("No pods available")
    if auto_refresh:
        time.sleep(refresh_interval)
        st.rerun()
    st.markdown("---")
    st.markdown(f"<div style='text-align: center; color: #666;'><p>Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p></div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
