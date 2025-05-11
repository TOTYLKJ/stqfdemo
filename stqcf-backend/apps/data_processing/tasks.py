from django.db import connections
from .utils import compute_morton

def test_process_tracks_data():
    """
    测试数据处理功能，从tracks_table读取数据，计算Morton码，
    并将结果写入trajectorydate表
    """
    try:
        # 连接MySQL数据库
        with connections['default'].cursor() as cursor:
            # 检查源表是否存在
            cursor.execute("""
                SELECT COUNT(*) 
                FROM information_schema.tables 
                WHERE table_schema = DATABASE() 
                AND table_name = 'tracks_table'
            """)
            if cursor.fetchone()[0] == 0:
                print("错误：tracks_table 表不存在！")
                return

            # 从tracks_table获取前5条数据
            cursor.execute("""
                SELECT track_id, latitude, longitude, time, keyword, date 
                FROM tracks_table
                LIMIT 5
            """)
            rows = cursor.fetchall()
            
            if not rows:
                print("警告：没有找到任何数据")
                return
            
            print(f"获取到 {len(rows)} 条数据")
            
            # 处理每一行数据
            for row in rows:
                try:
                    track_id, latitude, longitude, time, keyword, date = row
                    
                    # 数据类型验证
                    if not all(isinstance(x, (int, float)) for x in [latitude, longitude, time]):
                        print(f"\n数据类型错误: track_id={track_id}")
                        print(f"纬度类型: {type(latitude)}, 经度类型: {type(longitude)}, 时间类型: {type(time)}")
                        continue
                    
                    print(f"\n处理数据: track_id={track_id}")
                    print(f"输入参数: 纬度={latitude}, 经度={longitude}, 时间={time}")
                    
                    # 计算Morton码作为node_id
                    morton_code = compute_morton(latitude, longitude, time)
                    node_id = f"{morton_code[0]},{morton_code[1]}"  # 使用逗号分隔
                    print(f"计算得到的Morton码: {node_id}")
                    
                    # 插入数据到trajectorydate表，增加latitude, longitude, time字段
                    cursor.execute("""
                        INSERT INTO trajectorydate (keyword, node_id, traj_id, T_date, latitude, longitude, time)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, [keyword, node_id, track_id, date, latitude, longitude, time])
                    
                    # 验证插入是否成功
                    cursor.execute("""
                        SELECT keyword, node_id, traj_id, T_date, latitude, longitude, time
                        FROM trajectorydate 
                        WHERE traj_id = %s
                    """, [track_id])
                    result = cursor.fetchone()
                    if result:
                        print(f"插入成功: track_id={track_id}, node_id={node_id}")
                    else:
                        print(f"插入验证失败: track_id={track_id}")
                    
                except Exception as e:
                    print(f"处理数据时出错: track_id={track_id}, 错误信息={str(e)}")
                    continue

            # 提交事务
            cursor.execute("COMMIT")
            print("\n测试完成！")
            
    except Exception as e:
        print(f"测试过程中出现错误: {str(e)}")
        return

def clear_trajectorydate_table():
    """
    清空trajectorydate表
    """
    try:
        with connections['default'].cursor() as cursor:
            cursor.execute("TRUNCATE TABLE trajectorydate")
            cursor.execute("COMMIT")
            print("已清空trajectorydate表")
    except Exception as e:
        print(f"清空表时出错: {str(e)}")
        return False
    return True

def process_tracks_data():
    """
    从tracks_table读取数据（限制2000条），计算Morton码，
    并将结果写入trajectorydate表
    """
    try:
        # 连接MySQL数据库
        with connections['default'].cursor() as cursor:
            # 获取总记录数，限制为2000条
            total_count = 2000
            print(f"将处理 {total_count} 条记录")
            
            # 分批处理数据
            batch_size = 500  # 每批处理500条数据
            processed_count = 0
            error_count = 0
            success_count = 0
            
            while processed_count < total_count:
                # 获取一批数据
                cursor.execute("""
                    SELECT track_id, latitude, longitude, time, keyword, date 
                    FROM tracks_table
                    LIMIT %s OFFSET %s
                """, [batch_size, processed_count])
                rows = cursor.fetchall()
                
                if not rows:
                    break
                
                # 准备批量插入的数据
                batch_values = []
                current_batch_size = 0
                
                # 处理这批数据
                for row in rows:
                    try:
                        track_id, latitude, longitude, time, keyword, date = row
                        morton_code = compute_morton(latitude, longitude, time)
                        node_id = f"{morton_code[0]},{morton_code[1]}"
                        
                        # 添加到批量插入列表，增加latitude, longitude, time字段
                        batch_values.append((keyword, node_id, track_id, date, latitude, longitude, time))
                        current_batch_size += 1
                        
                        # 当累积100条数据时执行批量插入
                        if current_batch_size >= 100:
                            cursor.executemany("""
                                INSERT INTO trajectorydate (keyword, node_id, traj_id, T_date, latitude, longitude, time)
                                VALUES (%s, %s, %s, %s, %s, %s, %s)
                            """, batch_values)
                            success_count += current_batch_size
                            batch_values = []
                            current_batch_size = 0
                        
                    except Exception as e:
                        print(f"处理数据出错: track_id={track_id}, 错误信息={str(e)}")
                        error_count += 1
                        continue
                
                # 处理剩余的数据
                if batch_values:
                    try:
                        cursor.executemany("""
                            INSERT INTO trajectorydate (keyword, node_id, traj_id, T_date, latitude, longitude, time)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """, batch_values)
                        success_count += len(batch_values)
                    except Exception as e:
                        print(f"批量插入剩余数据时出错: {str(e)}")
                        error_count += len(batch_values)
                
                processed_count += len(rows)
                print(f"已处理: {processed_count}/{total_count} ({(processed_count/total_count*100):.2f}%)")
                print(f"成功: {success_count}, 失败: {error_count}")
                
                # 每批次提交一次事务
                cursor.execute("COMMIT")
                
                # 如果已经处理了2000条数据，就退出
                if processed_count >= total_count:
                    break
                
        print("\n处理完成！")
        print(f"总记录数: {total_count}")
        print(f"成功处理: {success_count}")
        print(f"处理失败: {error_count}")
        
    except Exception as e:
        print(f"处理数据时出现错误: {str(e)}")
        return 