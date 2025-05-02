import os
import sys
import shutil
from pathlib import Path
import docker
import tarfile
import io

def create_tar_bytes(source_path):
    """创建包含单个文件的tar字节流"""
    tar_stream = io.BytesIO()
    with tarfile.open(fileobj=tar_stream, mode='w') as tar:
        tar.add(source_path, arcname=os.path.basename(source_path))
    tar_stream.seek(0)
    return tar_stream

def distribute_public_key():
    """
    分发公钥到Docker容器中的各个雾服务器
    """
    public_key_path = Path('public_key.pkl')
    
    if not public_key_path.exists():
        print("错误：public_key.pkl 文件不存在")
        return False
    
    # 连接到Docker客户端
    client = docker.from_env()
    
    # 雾服务器容器名称列表
    fog_servers = [
        'fog1-server',
        'fog2-server',
        'fog3-server'
    ]
    
    # 创建tar文件字节流
    tar_stream = create_tar_bytes(public_key_path)
    
    for container_name in fog_servers:
        try:
            # 获取容器
            container = client.containers.get(container_name)
            
            if container.status != 'running':
                print(f"✗ 容器 {container_name} 未运行")
                continue
                
            print(f"正在分发公钥到 {container_name}...")
            
            # 在容器中创建目标目录
            container.exec_run('mkdir -p /app/keys')
            
            # 将公钥复制到容器中
            container.put_archive('/app/keys', tar_stream.getvalue())
            
            print(f"✓ 成功分发公钥到 {container_name}")
            
        except docker.errors.NotFound:
            print(f"✗ 未找到容器 {container_name}")
        except Exception as e:
            print(f"✗ 分发公钥到 {container_name} 失败: {str(e)}")
            continue

def check_local_keys():
    """检查本地密钥文件是否存在"""
    private_key_exists = Path('private_key.pkl').exists()
    public_key_exists = Path('public_key.pkl').exists()
    
    print("本地密钥检查:")
    print(f"{'✓' if private_key_exists else '✗'} private_key.pkl")
    print(f"{'✓' if public_key_exists else '✗'} public_key.pkl")
    
    return private_key_exists and public_key_exists

if __name__ == '__main__':
    if not check_local_keys():
        print("请确保 private_key.pkl 和 public_key.pkl 文件存在")
        sys.exit(1)
    
    distribute_public_key() 