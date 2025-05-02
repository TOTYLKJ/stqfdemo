def init_test_data():
    """初始化测试数据"""
    try:
        # 清理已有数据
        OctreeNode.objects.all().delete()
        TrajectoryDate.objects.all().delete()
        
        # 创建根节点
        root_node = OctreeNode.create(
            node_id=1,
            parent_id=None,  # 根节点的parent_id应为None
            level=1,
            is_leaf=0,
            MC=[1000, 2000],  # Morton码范围
            GC=[10, 20, 30, 15, 25, 35]  # 三维网格坐标 [min_x, min_y, min_z, max_x, max_y, max_z]
        )
        logger.info("根节点创建成功")
        
        # 创建子节点
        child_nodes = [
            {
                'node_id': 2,
                'parent_id': 1,
                'level': 2,
                'is_leaf': 1,
                'MC': [1000, 1500],
                'GC': [10, 20, 30, 12, 22, 32]  # 三维网格坐标
            },
            {
                'node_id': 3,
                'parent_id': 1,
                'level': 2,
                'is_leaf': 1,
                'MC': [1500, 2000],
                'GC': [12, 22, 32, 15, 25, 35]  # 三维网格坐标
            }
        ]
        
        for node_data in child_nodes:
            OctreeNode.create(**node_data)
        logger.info("子节点创建成功")
        
        # 创建轨迹数据
        crypto = HomomorphicProcessor()
        test_time = "2024-03-06 12:00:00"
        
        for node_id in [2, 3]:
            # 使用pickle序列化node_id
            enc_node_id = pickle.dumps(node_id, protocol=4)
            
            TrajectoryDate.create(
                keyword=b'test_keyword',
                node_id=enc_node_id,
                traj_id=pickle.dumps(f'traj_{node_id}', protocol=4),
                T_date=pickle.dumps('2024-03-06', protocol=4),
                latitude=pickle.dumps(crypto.public_key.encrypt(22.5), protocol=4),
                longitude=pickle.dumps(crypto.public_key.encrypt(113.5), protocol=4),
                time=pickle.dumps(test_time, protocol=4)
            )
        logger.info("轨迹数据创建成功")
        
    except Exception as e:
        logger.error(f"初始化测试数据失败: {str(e)}")
        raise

def test_sstp_query():
    """测试SSTP查询功能"""
    try:
        # 设置测试环境
        setup_mock_crypto()
        setup_cassandra()
        init_test_data()
        
        # 创建同态加密处理器
        crypto = HomomorphicProcessor()
        
        # 创建SSTP处理器实例
        processor = SSTPProcessor(fog_id=1)
        
        # 生成查询ID
        query_id = f"test_query_{uuid.uuid4().hex[:8]}"
        
        # 构建查询范围
        test_ranges = {
            'Mrange': {
                'morton_min': crypto.public_key.encrypt(1000),
                'morton_max': crypto.public_key.encrypt(2000)
            },
            'Grange': {
                'grid_min_x': crypto.public_key.encrypt(10.5),
                'grid_min_y': crypto.public_key.encrypt(20.3),
                'grid_min_z': crypto.public_key.encrypt(30.0),
                'grid_max_x': crypto.public_key.encrypt(15.8),
                'grid_max_y': crypto.public_key.encrypt(25.6),
                'grid_max_z': crypto.public_key.encrypt(35.0)
            },
            'Prange': {
                'latitude_min': crypto.public_key.encrypt(22.0),
                'longitude_min': crypto.public_key.encrypt(113.0),
                'time_min': crypto.public_key.encrypt(1709740800),  # 2024-03-06 00:00:00
                'latitude_max': crypto.public_key.encrypt(23.0),
                'longitude_max': crypto.public_key.encrypt(114.0),
                'time_max': crypto.public_key.encrypt(1709827199)   # 2024-03-06 23:59:59
            }
        }
        
        # 构建加密查询
        encrypted_query = {
            'rid': query_id,
            'keyword': b'test_keyword',
            'Mrange': {
                'morton_min': test_ranges['Mrange']['morton_min'],
                'morton_max': test_ranges['Mrange']['morton_max']
            },
            'Grange': {
                'grid_min_x': test_ranges['Grange']['grid_min_x'],
                'grid_min_y': test_ranges['Grange']['grid_min_y'],
                'grid_min_z': test_ranges['Grange']['grid_min_z'],
                'grid_max_x': test_ranges['Grange']['grid_max_x'],
                'grid_max_y': test_ranges['Grange']['grid_max_y'],
                'grid_max_z': test_ranges['Grange']['grid_max_z']
            },
            'Prange': {
                'latitude_min': test_ranges['Prange']['latitude_min'],
                'longitude_min': test_ranges['Prange']['longitude_min'],
                'time_min': test_ranges['Prange']['time_min'],
                'latitude_max': test_ranges['Prange']['latitude_max'],
                'longitude_max': test_ranges['Prange']['longitude_max'],
                'time_max': test_ranges['Prange']['time_max']
            }
        }
        
        # 处理查询
        logger.info(f"开始处理测试查询 {query_id}")
        logger.info(f"查询范围: {test_ranges}")
        result = processor.process_query(encrypted_query)
        
        # 验证结果
        assert result is not None, "查询结果不应为空"
        assert isinstance(result, dict), "结果应为字典类型"
        assert b'test_keyword' in result, "结果应包含测试关键词"
        assert query_id in result[b'test_keyword'], "结果应包含查询ID"
        
        # 验证结果格式
        trajectories = result[b'test_keyword'][query_id]
        assert isinstance(trajectories, dict), "轨迹结果应为字典类型"
        assert len(trajectories) > 0, "应至少包含一条轨迹"
        
        # 验证轨迹数据格式
        for tid, dates in trajectories.items():
            assert isinstance(dates, list), "日期应为列表类型"
            assert len(dates) > 0, "日期列表不应为空"
        
        logger.info(f"查询处理完成，结果: {result}")
        
        # 验证查询请求记录
        query_record = QueryRequest.objects.get(rid=query_id)
        assert query_record.status == "completed", "查询状态应为completed"
        
        return result
        
    except Exception as e:
        logger.error(f"测试过程中发生错误: {str(e)}")
        raise
    finally:
        # 清理测试数据
        try:
            OctreeNode.objects.all().delete()
            TrajectoryDate.objects.all().delete()
            QueryRequest.objects.all().delete()
        except Exception as e:
            logger.error(f"清理测试数据失败: {str(e)}") 