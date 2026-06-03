from machine import Pin, SoftI2C

# 使用你实际选择的引脚
i2c = SoftI2C(scl=Pin(1), sda=Pin(2), freq=400000)

print("扫描 I2C 设备...")
devices = i2c.scan()

if devices:
    print(f"找到设备: {[hex(d) for d in devices]}")
    if 0x29 in devices:
        print("✅ VL53L0X 连接成功！")
    else:
        print("⚠️ 未找到 0x29，检查：")
        print("  1. VIN 是否接了 5V（不是 3.3V）")
        print("  2. GND 是否接了 GND")
        print("  3. SDA/SCL 是否接对")
else:
    print("❌ 未找到任何设备，检查接线和供电")