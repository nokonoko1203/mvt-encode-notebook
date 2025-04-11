import math
import sys
import os
from pmtiles.writer import Writer
from pmtiles.tile import TileType, Compression


# --- HilbertカーブによるTileID計算 ---
def zxy_to_tileid(z, x, y):
    if z > 26:
        raise ValueError("Zoom level exceeds maximum (26)")
    if x >= (1 << z) or y >= (1 << z):
        raise ValueError(f"X/Y exceeds range for zoom {z}")
    if z == 0:
        return 0
    tile_id = 0
    n = 1 << z
    cur_x, cur_y = x, y
    for i in range(z - 1, -1, -1):
        level_n = 1 << i
        rx = (cur_x >> i) & 1
        ry = (cur_y >> i) & 1
        quadrant = (rx * 3) ^ ry
        tile_id += quadrant * (level_n * level_n)
        cur_x, cur_y = _rot(level_n, cur_x % level_n, cur_y % level_n, rx, ry)
    offset = (n * n - 1) // 3
    tile_id += offset
    return tile_id


def _rot(n, x, y, rx, ry):
    if ry == 0:
        if rx == 1:
            x = n - 1 - x
            y = n - 1 - y
        x, y = y, x
    return x, y


# --- 座標計算ヘルパー ---
def tile_center(z, x, y):
    lon_min, lat_min, lon_max, lat_max = tile_bounds(z, x, y)
    center_lon = (lon_min + lon_max) / 2
    center_lat = (lat_min + lat_max) / 2
    return center_lon, center_lat, z


def tile_bounds(z, x, y):
    lat_max, lon_min = num2deg(x, y, z)
    lat_min, lon_max = num2deg(x + 1, y + 1, z)
    return lon_min, lat_min, lon_max, lat_max


def num2deg(xtile, ytile, zoom):
    n = 1 << zoom
    lon_deg = xtile / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * ytile / n)))
    lat_deg = math.degrees(lat_rad)
    return lat_deg, lon_deg


# --- メイン処理: 単一MVTタイルからPMTiles v3を作成 ---
def create_single_tile_pmtiles(mvt_input_path, pmtiles_output_path, z, x, y):
    """
    【pmtilesライブラリ使用版】単一MVTタイルからPMTiles v3を作成する。

    Args:
        mvt_input_path (str): 入力MVTファイルのパス。
        pmtiles_output_path (str): 出力PMTilesファイルのパス。
        z (int): タイルのズームレベル。
        x (int): タイルのX座標。
        y (int): タイルのY座標。
    """
    try:
        # --- 1. タイルデータの読み込み ---
        with open(mvt_input_path, "rb") as f:
            tile_data = f.read()

        # --- 2. TileID の計算 ---
        tile_id = zxy_to_tileid(z, x, y)

        # --- 3. PMTilesライターの初期化 ---
        # 出力ファイルをバイナリ書き込みモードで開く
        with open(pmtiles_output_path, "wb") as f:
            writer = Writer(f)

            # --- 4. MVTタイルデータの書き込み ---
            writer.write_tile(tile_id, tile_data)

            # --- 5. PMTilesファイルのファイナライズ ---
            # ヘッダー情報を辞書として定義
            header = {
                "min_zoom": z,
                "max_zoom": z,
                "min_lon_e7": int(-180.0 * 10000000),  # 仮の値。必要に応じて調整
                "min_lat_e7": int(-85.05112878 * 10000000),  # 仮の値。必要に応じて調整
                "max_lon_e7": int(180.0 * 10000000),  # 仮の値。必要に応じて調整
                "max_lat_e7": int(85.05112878 * 10000000),  # 仮の値。必要に応じて調整
                "center_zoom": z,
                "center_lon_e7": 0,  # 仮の値。必要に応じて調整
                "center_lat_e7": 0,  # 仮の値。必要に応じて調整
                "tile_type": TileType.MVT,
                "tile_compression": Compression.GZIP,
            }
            # メタデータを辞書として定義
            metadata = {"name": "test_pmtiles_lib"}

            # finalizeメソッドを呼び出してファイル構造を完成させる
            writer.finalize(header, metadata)

        print(f"PMTilesファイルを作成しました: {pmtiles_output_path}")

    except Exception as e:
        print(f"エラーが発生しました: {e}", file=sys.stderr)
        sys.exit(1)


# --- 使用例 ---
if __name__ == "__main__":
    input_mvt = "./14/8907/5509.mvt"
    output_pmtiles = "output.pmtiles"  # PMTilesファイル名
    tile_z, tile_x, tile_y = 14, 8907, 5509

    # ディレクトリが存在しない場合は作成
    os.makedirs(os.path.dirname(input_mvt), exist_ok=True)

    # ダミーMVTファイルを作成 (既存の場合はスキップ)
    if not os.path.exists(input_mvt):
        print(f"ダミーMVTファイルを作成中: {input_mvt}")
        # 非常に単純なバイト列。実際のMVTではない。
        # gzip圧縮を考慮して、少し長めのデータにする
        dummy_mvt_content = b"\\x1a" + b"\\x00" * 100
        with open(input_mvt, "wb") as f:
            f.write(dummy_mvt_content)
        print("ダミーMVTファイルを作成しました。")
    else:
        print(f"既存のMVTファイルを使用: {input_mvt}")

    print(
        f"入力: {input_mvt}, 出力: {output_pmtiles}, タイル: z={tile_z}, x={tile_x}, y={tile_y}"
    )
    create_single_tile_pmtiles(input_mvt, output_pmtiles, tile_z, tile_x, tile_y)
    print("\\nPMTilesファイルの情報を表示します:")
    os.system(f"pmtiles show {output_pmtiles}")
    print("\\nPMTilesファイルの検証を実行します:")
    os.system(f"pmtiles verify {output_pmtiles}")
