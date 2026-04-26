def simplify_points(points, max_gap=3):
    if len(points) < 3:
        return points

    result = [points[0]]
    i = 1
    while i < len(points):
        current_p = points[i]
        last_kept = result[-1]
        
        next_idx = i + 1
        while next_idx < len(points):
            next_p = points[next_idx]
            
            is_horizontal = (current_p[1] == last_kept[1] == next_p[1])
            is_vertical = (current_p[0] == last_kept[0] == next_p[0])
            
            if is_horizontal or is_vertical:
                dist = max(abs(next_p[0] - last_kept[0]), abs(next_p[1] - last_kept[1]))
                
                if dist <= max_gap:
                    next_idx += 1
                else:
                    break
            else:
                break
        
        target_point = points[next_idx - 1]
        if target_point != last_kept:
            result.append(target_point)
        
        i = next_idx

    if result[-1] != points[-1]:
        result.append(points[-1])
        
    return result

def generate_hitbox(img, sampling=4):
    """
    根據圖片的 Alpha 通道產出相對於中心點的 hitbox 座標
    sampling: 取樣頻率，數值越高頂點越少（效能越好），預設為 4。
    """
    # 取得圖片尺寸
    width, height = img.size
    center_x, center_y = width / 2, height / 2
    
    # 取得 Alpha 通道資料
    alpha = img.getchannel('A')
    pixels = alpha.load()

    points = []
    
    # 簡單的掃描演算法：掃描四周邊緣點
    # 頂部邊緣
    for x in range(0, width, sampling):
        for y in range(height):
            if pixels[x, y] > 0:
                points.append((x - center_x, center_y - y))
                break
    
    # 右側邊緣
    for y in range(0, height, sampling):
        for x in range(width - 1, -1, -1):
            if pixels[x, y] > 0:
                points.append((x - center_x, center_y - y))
                break

    # 底部邊緣 (由右往左)
    for x in range(width - 1, -1, -sampling):
        for y in range(height - 1, -1, -1):
            if pixels[x, y] > 0:
                points.append((x - center_x, center_y - y))
                break

    # 左側邊緣 (由下往上)
    for y in range(height - 1, -1, -sampling):
        for x in range(width):
            if pixels[x, y] > 0:
                points.append((x - center_x, center_y - y))
                break

    # 去除重複並保持順序
    seen = set()
    ordered_points = []
    for p in points:
        if p not in seen:
            ordered_points.append(p)
            seen.add(p)
    # 去共線點
    ordered_points = simplify_points(ordered_points, max_gap=3)

    return ordered_points