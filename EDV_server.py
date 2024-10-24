# Importing necessary modules
import streamlit as st
import dropbox
import qrcode
from PIL import Image
import json
import io
import requests

# Homepage
st.set_page_config(page_title=" 🗄️ EDV file uploader")
st.header("EDV file uploader")
st.subheader('Upload files to store and retrieve Dropbox links and QR codes')

# Get secrets from Streamlit secrets management
ACCESS_TOKEN = st.secrets["dropbox"]["access_token"]
REFRESH_TOKEN = st.secrets["dropbox"]["refresh_token"]
CLIENT_ID = st.secrets["dropbox"]["client_id"]
CLIENT_SECRET = st.secrets["dropbox"]["client_secret"]

# Initialize Dropbox client
dbx = dropbox.Dropbox(ACCESS_TOKEN)

# Function to refresh access token
def refresh_access_token():
    global ACCESS_TOKEN, REFRESH_TOKEN, dbx  # Declare global variables
    url = "https://api.dropboxapi.com/oauth2/token"
    data = {
        "grant_type": "refresh_token",
        "refresh_token": REFRESH_TOKEN,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    }
    response = requests.post(url, data=data)
    
    if response.status_code == 200:
        # Update global variables with new tokens
        ACCESS_TOKEN = response.json().get("access_token")
        REFRESH_TOKEN = response.json().get("refresh_token")
        dbx = dropbox.Dropbox(ACCESS_TOKEN)  # Re-initialize Dropbox client
        return True
    else:
        st.error(f"Failed to refresh access token: {response.json()}")
        return False

# Function to upload a file to Dropbox and get the link
def upload_to_dropbox(uploadedfile, filename):
    global dbx  # Declare dbx as global
    try:
        file_path = f"/EDV/{filename}"
        dbx.files_upload(uploadedfile.getbuffer().tobytes(), file_path)
        shared_link_metadata = dbx.sharing_create_shared_link_with_settings(file_path)
        file_link = shared_link_metadata.url.replace('?dl=0', '?dl=1')  # Direct download link
        return file_link
    except dropbox.exceptions.AuthError as e:
        # If there's an auth error, refresh the access token
        st.warning("Access token expired. Refreshing token...")
        if refresh_access_token():
            # Retry file upload after refreshing token
            return upload_to_dropbox(uploadedfile, filename)
        else:
            st.error("Failed to refresh access token. Please check your credentials.")
            return None

# Function to generate QR code with metadata
def generate_qr_code_with_metadata(files_metadata):
    metadata = {"files": files_metadata}  # Embed list of files and their metadata
    qr_data = json.dumps(metadata)
    
    # Generate the QR code
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(qr_data)
    qr.make(fit=True)
    img = qr.make_image(fill='black', back_color='white')
    
    return img

# Function to convert PIL Image to bytes
def pil_image_to_bytes(img):
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    byte_im = buf.getvalue()
    return byte_im

# Upload section
uploaded_files = st.file_uploader('Upload multiple documents (Aadhaar, PAN, etc.)', type=['pdf', 'jpeg', 'jpg', 'png'], accept_multiple_files=True)

if uploaded_files is not None:
    files_metadata = []
    
    # Loop through each uploaded file
    for uploaded_file in uploaded_files:
        document_type = st.selectbox(f"Select document type for {uploaded_file.name}", ["Aadhaar", "PAN", "Passport", "Other"])
        
        # Upload file to Dropbox
        file_link = upload_to_dropbox(uploaded_file, uploaded_file.name)
        if file_link:
            # Add file metadata (link and document type)
            files_metadata.append({
                "document_url": file_link,
                "document_type": document_type
            })
    
    # Generate QR code for all uploaded files' metadata
    if files_metadata:
        qr_image = generate_qr_code_with_metadata(files_metadata)
        qr_image_bytes = pil_image_to_bytes(qr_image)
        
        # Display QR code
        st.image(qr_image_bytes, caption='QR code with metadata for uploaded files')
        
        # Download button for QR code
        st.download_button(label="Download QR code", data=qr_image_bytes, file_name="qr_code.png", mime="image/png")
