# -*- mode: python ; coding: utf-8 -*-


block_cipher = None


a = Analysis(['bot_main.py'],
             pathex=['C:\\Users\\klime\\VS Code\\selenium_chrome'],
             binaries=[],
             datas=[('.venv_tribal_wars\\Lib\\site-packages\\ttkbootstrap', 'ttkbootstrap'),
		    ('.venv_tribal_wars\\Lib\\site-packages\\selenium\\webdriver', 'selenium\\webdriver'),
		    ('.venv_tribal_wars\\Lib\\site-packages\\certifi\\cacert.pem', 'certifi'),
                    ('icons', 'icons'), ('anticaptcha-plugin.reg', '.'), ('0.60_0.crx', '.')],
             hiddenimports=['ttkbootstrap', 'selenium', 'lxml._elementpath'],
             hookspath=[],
             hooksconfig={},
             runtime_hooks=[],
             excludes=['_bootlocale'],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)

exe = EXE(pyz,
          a.scripts, 
          [],
          exclude_binaries=True,
          name='tribal_wars',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=False,
          disable_windowed_traceback=False,
          target_arch=None,
          codesign_identity=None,
          entitlements_file=None )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas, 
               strip=False,
               upx=True,
               upx_exclude=[],
               name='tribal_wars')
