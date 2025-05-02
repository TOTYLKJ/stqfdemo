#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import json
import pickle
from pathlib import Path

# 设置基本路径
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# 创建一个简化版的ExtendedHomomorphicProcessor类，不依赖于Django设置
class SimpleHomomorphicProcessor:
    """简化版的同态加密处理器，用于测试解密功能"""
    
    def __init__(self):
        """初始化处理器"""
        self.private_key = self._load_private_key()
        
    def _load_private_key(self):
        """从配置加载私钥"""
        try:
            # 尝试从应用目录加载
            key_path = os.path.join(BASE_DIR, 'keys', 'private_key.pkl')
            if os.path.exists(key_path):
                print(f"从 {key_path} 加载私钥")
                with open(key_path, 'rb') as f:
                    return pickle.load(f)
            
            # 尝试从项目根目录加载
            key_path = os.path.join(BASE_DIR, 'private_key.pkl')
            if os.path.exists(key_path):
                print(f"从 {key_path} 加载私钥")
                with open(key_path, 'rb') as f:
                    return pickle.load(f)
                    
            print("未找到私钥文件")
            return None
        except Exception as e:
            print(f"加载私钥失败: {str(e)}")
            return None
    
    def decrypt_hex_string(self, hex_string):
        """解密十六进制字符串表示的加密值"""
        try:
            # 如果输入为None，直接返回
            if hex_string is None:
                return None
                
            # 检查是否是十六进制字符串
            if not all(c in '0123456789abcdefABCDEF' for c in hex_string):
                return hex_string
                
            # 尝试将十六进制字符串转换为字节
            try:
                binary_data = bytes.fromhex(hex_string)
            except ValueError:
                # 如果不是有效的十六进制字符串，直接返回原值
                return hex_string
            
            # 检查是否是Paillier加密对象
            # 注意：Paillier加密对象序列化后通常很大（几千字节）
            if len(binary_data) > 1000:  # 可能是序列化的Paillier对象
                try:
                    # 尝试反序列化
                    try:
                        from phe import paillier  # 确保导入Paillier库
                    except ImportError:
                        print("警告: 无法导入paillier库，无法解密Paillier对象")
                        return f"Encrypted(Unknown)"
                        
                    encrypted_obj = pickle.loads(binary_data)
                    
                    # 检查是否是Paillier加密对象
                    if hasattr(encrypted_obj, 'n') and hasattr(encrypted_obj, 'ciphertext'):
                        # 是Paillier加密对象，使用私钥解密
                        if self.private_key:
                            decrypted = self.private_key.decrypt(encrypted_obj)
                            return decrypted
                        else:
                            print("私钥未加载，无法解密Paillier对象")
                            return f"Encrypted(Paillier)"
                    else:
                        # 不是Paillier对象，但是序列化的对象
                        return f"Serialized({type(encrypted_obj).__name__})"
                except Exception as e:
                    print(f"反序列化大型对象失败: {str(e)}")
                    return f"Binary({len(binary_data)} bytes)"
            
            # 对于较小的二进制数据，尝试其他解析方法
            # 尝试解析为整数（如果是4或8字节）
            if len(binary_data) == 4:
                import struct
                try:
                    return struct.unpack('!I', binary_data)[0]  # 大端序无符号整数
                except:
                    pass
            elif len(binary_data) == 8:
                import struct
                try:
                    return struct.unpack('!Q', binary_data)[0]  # 大端序无符号长整数
                except:
                    pass
            
            # 尝试解码为UTF-8字符串
            try:
                return binary_data.decode('utf-8')
            except UnicodeDecodeError:
                # 如果无法解码为字符串，返回十六进制表示
                return f"Binary({len(binary_data)} bytes)"
                    
        except Exception as e:
            print(f"解密十六进制字符串失败: {str(e)}")
            return hex_string

def test_simple_crypto_processor():
    """测试SimpleHomomorphicProcessor的解密功能"""
    print("=" * 50)
    print("测试SimpleHomomorphicProcessor的解密功能")
    print("=" * 50)
    
    # 初始化SimpleHomomorphicProcessor
    crypto = SimpleHomomorphicProcessor()
    
    # 检查私钥是否加载成功
    if crypto.private_key:
        print("私钥加载成功")
    else:
        print("私钥加载失败，但仍将继续测试基本解密功能")
    
    # 测试解密方法
    print("\n测试decrypt_hex_string方法:")
    
    # 测试用例
    test_cases = [
        # 测试非十六进制字符串
        "hello world",
        # 测试有效的十六进制字符串（但不是加密对象）
        "48656c6c6f20576f726c64",  # "Hello World" 的十六进制
        # 测试无效的十六进制字符串
        "ZZZZ",
        # 测试None值
        None,
        # 测试4字节整数
        "00000001",  # 1的十六进制
        # 测试8字节整数
        "0000000000000064",  # 100的十六进制
        # 测试UTF-8字符串
        "e4b8ade69687",  # "中文"的十六进制
    ]
    
    for i, test_case in enumerate(test_cases):
        print(f"\n测试用例 {i+1}: {test_case}")
        result = crypto.decrypt_hex_string(test_case)
        print(f"解密结果: {result}")
        
    print("\n" + "=" * 50)

def main():
    """主函数"""
    print("开始测试解密功能")
    
    # 测试SimpleHomomorphicProcessor
    test_simple_crypto_processor()
    
    print("\n测试完成")

if __name__ == "__main__":
    main() 