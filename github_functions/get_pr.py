import requests
from base64 import b64decode


def get_user_prs(username, token):
    url = f'https://api.github.com/search/issues?q=is:pr+author:{username}+is:open'
    headers = {'Authorization': f'token {token}'}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()['items']

def get_pr_files(owner, repo, pull_number, token):
    url = f'https://api.github.com/repos/{owner}/{repo}/pulls/{pull_number}/files'
    headers = {'Authorization': f'token {token}'}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()

def get_file_content(file_url, token:str,file:dict):
    headers = {'Authorization': f'token {token}'}
    response = requests.get(file_url, headers=headers)
    response.raise_for_status()

    file_data = response.json()
    
    # print(file_data)
    patch_content = file.get('patch', '')
    
    # Split the patch content into lines
    patch_lines = patch_content.split('\n')
    
    # Identify added and removed lines
    added_lines = []
    removed_lines = []
    
    for line in patch_lines:
        if line.startswith('+') and not line.startswith('+++'):
            print(True)
            added_lines.append(line[1:])
        elif line.startswith('-') and not line.startswith('---'):
            removed_lines.append(line[1:])
    
    print("\nAdded Lines:")
    for added_line in added_lines:
        print(f"+ {added_line}")
        
    print("\nRemoved Lines:")
    for removed_line in removed_lines:
        print(f"- {removed_line}")

    content = file_data.get('content', '')
    if content:
        decoded_content = patch_content+b64decode(content).decode('utf-8')
    else:
        decoded_content = ''
    
    # Write the decoded content to the file as well
    with open("temp.txt", 'w') as file:
        file.write(decoded_content)
    
    return decoded_content

