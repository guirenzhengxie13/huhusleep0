@echo off
setlocal enabledelayedexpansion

echo ========================================
echo Start backup - no overwrite mode
echo ========================================
echo.

call :BackupOne "Jiangyan-device_status" "C:\Users\Lenovo\Desktop\data\测试跟踪\姜堰\device_status" "\\TAIHU\public\公共\步步安_呼呼睡持续跟踪\呼呼睡持续跟踪\姜堰福利院\测试情况跟踪\姜堰福利院测试情况跟踪"
call :BackupOne "Jiangyan-identity_2d43" "C:\Users\Lenovo\Desktop\data\测试跟踪\姜堰\identity_2d43" "\\TAIHU\public\公共\步步安_呼呼睡持续跟踪\呼呼睡持续跟踪\姜堰福利院\测试情况跟踪\每日数据拉取"

call :BackupOne "Hefei-device_status" "C:\Users\Lenovo\Desktop\data\测试跟踪\合肥\device_status" "\\TAIHU\public\公共\步步安_呼呼睡持续跟踪\呼呼睡持续跟踪\合肥养老院\测试情况跟踪\表格整理"
call :BackupOne "Hefei-identity_2d43" "C:\Users\Lenovo\Desktop\data\测试跟踪\合肥\identity_2d43" "\\TAIHU\public\公共\步步安_呼呼睡持续跟踪\呼呼睡持续跟踪\合肥养老院\测试情况跟踪\数据拉取"

call :BackupOne "Nanjing-device_status" "C:\Users\Lenovo\Desktop\data\测试跟踪\南京\device_status" "\\TAIHU\public\公共\步步安_呼呼睡持续跟踪\呼呼睡持续跟踪\南京机构\测试情况跟踪\表格整理"
call :BackupOne "Nanjing-identity_2d43" "C:\Users\Lenovo\Desktop\data\测试跟踪\南京\identity_2d43" "\\TAIHU\public\公共\步步安_呼呼睡持续跟踪\呼呼睡持续跟踪\南京机构\测试情况跟踪\数据拉取"

echo.
echo ========================================
echo All backup finished.
echo Existing files/folders were skipped.
echo ========================================
pause
exit /b


:BackupOne
set "NAME=%~1"
set "SRC=%~2"
set "DST=%~3"

echo.
echo ----------------------------------------
echo Backup: %NAME%
echo SRC=%SRC%
echo DST=%DST%
echo ----------------------------------------

if not exist "%SRC%" (
    echo ERROR: Source folder not found. Skip %NAME%.
    goto :eof
)

if not exist "%DST%" (
    echo Destination folder not found. Create: %DST%
    mkdir "%DST%" 2>nul
)

if not exist "%DST%" (
    echo ERROR: Cannot access destination folder. Skip %NAME%.
    goto :eof
)

rem Copy files directly under source folder, no overwrite.
for %%F in ("%SRC%\*") do (
    if exist "%%F" (
        if not exist "%DST%\%%~nxF" (
            echo Copy file: %%~nxF
            copy "%%F" "%DST%\" >nul
        ) else (
            echo Skip file: %%~nxF already exists.
        )
    )
)

rem Copy subfolders directly under source folder.
rem If the same folder already exists in destination, skip the whole folder.
for /d %%D in ("%SRC%\*") do (
    set "FOLDER=%%~nxD"

    if exist "%DST%\!FOLDER!" (
        echo Skip folder: !FOLDER! already exists.
    ) else (
        echo Copy folder: !FOLDER!
        xcopy "%%D" "%DST%\!FOLDER!\" /E /I /H /Y >nul
    )
)

echo Done: %NAME%
goto :eof
