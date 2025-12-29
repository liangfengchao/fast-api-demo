"""
测试路由是否正确注册
运行方式: python test_routes.py
"""
try:
    from app.main import app
    
    print("=" * 50)
    print("已注册的路由:")
    print("=" * 50)
    
    routes = []
    for route in app.routes:
        if hasattr(route, 'path') and hasattr(route, 'methods'):
            for method in route.methods:
                if method != 'HEAD':  # 排除HEAD方法
                    routes.append(f"{method:6} {route.path}")
    
    routes.sort()
    for route in routes:
        print(route)
    
    print("=" * 50)
    print(f"总共 {len(routes)} 个路由")
    
    # 检查认证路由
    auth_routes = [r for r in routes if '/auth' in r]
    if auth_routes:
        print("\n认证相关路由:")
        for route in auth_routes:
            print(f"  ✓ {route}")
    else:
        print("\n⚠ 警告: 未找到认证路由!")
        
except Exception as e:
    print(f"错误: {e}")
    import traceback
    traceback.print_exc()

