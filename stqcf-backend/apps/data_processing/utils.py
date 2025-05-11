def compute_morton(latitude, longitude, time):
    # 处理纬度的两位编码
    lat_bit1 = 1 if latitude >= 0 else 0
    if lat_bit1 == 1:
        mid_lat = 45
    else:
        mid_lat = -45
    lat_bit2 = 1 if latitude >= mid_lat else 0
    
    # 处理经度的两位编码
    lon_bit1 = 1 if longitude >= 0 else 0
    if lon_bit1 == 1:
        mid_lon = 90
    else:
        mid_lon = -90
    lon_bit2 = 1 if longitude >= mid_lon else 0
    
    # 处理时间的两位编码
    time_bit1 = 1 if time >= 108000 else 0
    if time_bit1 == 1:
        mid_time = 162000
    else:
        mid_time = 54000
    time_bit2 = 1 if time >= mid_time else 0
    
    # 交叉组合二进制位
    combined_bits = [
        lat_bit1, lon_bit1, time_bit1,
        lat_bit2, lon_bit2, time_bit2
    ]
    
    # 将前三位和后三位转换为十进制
    part1 = (combined_bits[0] << 2) | (combined_bits[1] << 1) | combined_bits[2]
    part2 = (combined_bits[3] << 2) | (combined_bits[4] << 1) | combined_bits[5]
    
    return [part1-1, part2] 