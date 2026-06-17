@echo off
setlocal enabledelayedexpansion

echo ========================================
echo Start backup - no overwrite mode
echo ========================================
echo.

call :BackupOne "HK" "C:\Users\Lenovo\Desktop\data\香港\timeline" "\\TAIHU\public\公共\步步安_呼呼睡持续跟踪\呼呼睡持续跟踪\香港钧溢养老院\数据整理\8点数据"
call :BackupOne "HK" "C:\Users\Lenovo\Desktop\data\香港\timeline" "\\TAIHU\public\公共\步步安_呼呼睡持续跟踪\呼呼睡持续跟踪\香港钧溢养老院\数据整理\6月" "COPY_DIR"
call :BackupRawData "HK" "C:\Users\Lenovo\Desktop\data\香港\rawdata" "\\TAIHU\public\公共\步步安_呼呼睡持续跟踪\呼呼睡持续跟踪\香港钧溢养老院\数据整理\6月"

call :BackupOne "Jiangyan" "C:\Users\Lenovo\Desktop\data\姜堰\timeline" "\\TAIHU\public\公共\步步安_呼呼睡持续跟踪\呼呼睡持续跟踪\姜堰福利院\数据解析\解析的数据\呼吸心率8点"
call :BackupOne "Jiangyan" "C:\Users\Lenovo\Desktop\data\姜堰\timeline" "\\TAIHU\public\公共\步步安_呼呼睡持续跟踪\呼呼睡持续跟踪\姜堰福利院\数据解析\解析的数据\6月份" "COPY_DIR"
call :BackupRawData "Jiangyan" "C:\Users\Lenovo\Desktop\data\姜堰\rawdata" "\\TAIHU\public\公共\步步安_呼呼睡持续跟踪\呼呼睡持续跟踪\姜堰福利院\数据解析\解析的数据\6月份"
call :BackupSleepReport "Jiangyan" "C:\Users\Lenovo\Desktop\data\姜堰\rawdata" "\\TAIHU\public\公共\步步安_呼呼睡持续跟踪\呼呼睡持续跟踪\姜堰福利院\数据解析\解析的数据\睡眠报告"

call :BackupOne "Hefei" "C:\Users\Lenovo\Desktop\data\合肥\timeline" "\\TAIHU\public\公共\步步安_呼呼睡持续跟踪\呼呼睡持续跟踪\合肥养老院\数据解析\解析的数据\呼吸心率8点"
call :BackupOne "Hefei" "C:\Users\Lenovo\Desktop\data\合肥\timeline" "\\TAIHU\public\公共\步步安_呼呼睡持续跟踪\呼呼睡持续跟踪\合肥养老院\数据解析\解析的数据\6月份" "COPY_DIR"
call :BackupRawData "Hefei" "C:\Users\Lenovo\Desktop\data\合肥\rawdata" "\\TAIHU\public\公共\步步安_呼呼睡持续跟踪\呼呼睡持续跟踪\合肥养老院\数据解析\解析的数据\6月份"
call :BackupSleepReport "Hefei" "C:\Users\Lenovo\Desktop\data\合肥\rawdata" "\\TAIHU\public\公共\步步安_呼呼睡持续跟踪\呼呼睡持续跟踪\合肥养老院\数据解析\解析的数据\睡眠报告"

call :BackupOne "Nanjing" "C:\Users\Lenovo\Desktop\data\南京\timeline" "\\TAIHU\public\公共\步步安_呼呼睡持续跟踪\呼呼睡持续跟踪\南京机构\呼吸心率8点"
call :BackupOne "Nanjing" "C:\Users\Lenovo\Desktop\data\南京\timeline" "\\TAIHU\public\公共\步步安_呼呼睡持续跟踪\呼呼睡持续跟踪\南京机构\6月份" "COPY_DIR"
call :BackupRawData "Nanjing" "C:\Users\Lenovo\Desktop\data\南京\rawdata" "\\TAIHU\public\公共\步步安_呼呼睡持续跟踪\呼呼睡持续跟踪\南京机构\6月份"
call :BackupSleepReport "Nanjing" "C:\Users\Lenovo\Desktop\data\南京\rawdata" "\\TAIHU\public\公共\步步安_呼呼睡持续跟踪\呼呼睡持续跟踪\南京机构\睡眠报告"

call :BackupOne "Wuzhou" "C:\Users\Lenovo\Desktop\data\梧州\timeline" "\\TAIHU\public\公共\步步安_呼呼睡持续跟踪\呼呼睡持续跟踪\梧州养老院\数据解析\呼吸心率8点"
call :BackupOne "Wuzhou" "C:\Users\Lenovo\Desktop\data\梧州\timeline" "\\TAIHU\public\公共\步步安_呼呼睡持续跟踪\呼呼睡持续跟踪\梧州养老院\数据解析\6月份" "COPY_DIR"
call :BackupRawData "Wuzhou" "C:\Users\Lenovo\Desktop\data\梧州\rawdata" "\\TAIHU\public\公共\步步安_呼呼睡持续跟踪\呼呼睡持续跟踪\梧州养老院\数据解析\6月份"
call :BackupSleepReport "Wuzhou" "C:\Users\Lenovo\Desktop\data\梧州\rawdata" "\\TAIHU\public\公共\步步安_呼呼睡持续跟踪\呼呼睡持续跟踪\梧州养老院\数据解析\睡眠报告"

call :BackupOne "Yancheng" "C:\Users\Lenovo\Desktop\data\盐城\timeline" "\\TAIHU\public\公共\步步安_呼呼睡持续跟踪\呼呼睡持续跟踪\盐城养老院\数据解析\呼吸心率8点"
call :BackupOne "Yancheng" "C:\Users\Lenovo\Desktop\data\盐城\timeline" "\\TAIHU\public\公共\步步安_呼呼睡持续跟踪\呼呼睡持续跟踪\盐城养老院\数据解析\6月份" "COPY_DIR"
call :BackupRawData "Yancheng" "C:\Users\Lenovo\Desktop\data\盐城\rawdata" "\\TAIHU\public\公共\步步安_呼呼睡持续跟踪\呼呼睡持续跟踪\盐城养老院\数据解析\6月份"
call :BackupSleepReport "Yancheng" "C:\Users\Lenovo\Desktop\data\盐城\rawdata" "\\TAIHU\public\公共\步步安_呼呼睡持续跟踪\呼呼睡持续跟踪\盐城养老院\数据解析\睡眠报告"


call :BackupOne "CompanyTest" "C:\Users\Lenovo\Desktop\data\公司内测\timeline" "\\TAIHU\public\公共\步步安_呼呼睡持续跟踪\呼呼睡持续跟踪\公司内测\8点数据"
call :BackupOne "CompanyTest" "C:\Users\Lenovo\Desktop\data\公司内测\timeline" "\\TAIHU\public\公共\步步安_呼呼睡持续跟踪\呼呼睡持续跟踪\公司内测\原始数据" "COPY_DIR"
call :BackupRawData "CompanyTest" "C:\Users\Lenovo\Desktop\data\公司内测\rawdata" "\\TAIHU\public\公共\步步安_呼呼睡持续跟踪\呼呼睡持续跟踪\公司内测\原始数据"
call :BackupSleepReport "CompanyTest" "C:\Users\Lenovo\Desktop\data\公司内测\rawdata" "\\TAIHU\public\公共\步步安_呼呼睡持续跟踪\呼呼睡持续跟踪\公司内测\睡眠报告"


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
set "MODE=%~4"

echo.
echo ----------------------------------------
echo Backup: %NAME%
echo SRC=%SRC%
echo DST=%DST%
echo MODE=%MODE%
echo ----------------------------------------

if not exist "%SRC%" (
    echo ERROR: Source folder not found. Skip %NAME%.
    goto :eof
)

if "%MODE%"=="COPY_DIR" (
    if not exist "%DST%" (
        echo ERROR: Destination root folder not found. Skip %NAME%.
        goto :eof
    )

    for /d %%D in ("%SRC%\*") do (
        set "DATEFOLDER=%%~nxD"

        if exist "%DST%\!DATEFOLDER!" (
            echo Skip folder: !DATEFOLDER! already exists.
        ) else (
            echo Copy folder: !DATEFOLDER!
            xcopy "%%D" "%DST%\!DATEFOLDER!" /E /I /H /Y >nul
        )
    )

    echo Done: %NAME%
    goto :eof
)

pushd "%DST%"
if errorlevel 1 (
    echo ERROR: Cannot access destination folder. Skip %NAME%.
    goto :eof
)

for /d %%D in ("%SRC%\*") do (
    for /d %%E in ("%%D\*") do (
        set "DEVICE=%%~nxE"

        if not exist "!DEVICE!" (
            mkdir "!DEVICE!"
        )

        for %%F in ("%%E\*.csv") do (
            if exist "%%F" (
                if not exist "!DEVICE!\%%~nxF" (
                    echo Copy: %%~nxF  to  !DEVICE!
                    copy "%%F" "!DEVICE!" >nul
                ) else (
                    echo Skip: %%~nxF already exists in !DEVICE!
                )
            )
        )
    )
)

popd
echo Done: %NAME%
goto :eof


:BackupRawData
set "NAME=%~1"
set "SRC=%~2"
set "DSTROOT=%~3"

echo.
echo ----------------------------------------
echo RawData Backup: %NAME%
echo SRC=%SRC%
echo DSTROOT=%DSTROOT%
echo ----------------------------------------

if not exist "%SRC%" (
    echo ERROR: RawData source not found. Skip %NAME%.
    goto :eof
)

if not exist "%DSTROOT%" (
    echo ERROR: Destination root not found. Skip %NAME%.
    goto :eof
)

for /d %%D in ("%SRC%\*") do (
    set "FULLDATE=%%~nxD"
    set "SHORTDATE=!FULLDATE!"

    rem 20260506 -> 506
    if "!FULLDATE:~0,6!"=="202605" (
        set "SHORTDATE=!FULLDATE:~5,3!"
    )

    if not exist "%DSTROOT%\!SHORTDATE!" (
        echo Skip rawdata: target date folder not found: !SHORTDATE!
    ) else (
        echo RawData date: !FULLDATE!  to  !SHORTDATE!

        for %%F in ("%%D\*") do (
            if exist "%%F" (
                set "FILENAME=%%~nxF"

                echo !FILENAME! | findstr /B /I "sorted" >nul
                if errorlevel 1 (
                    if not exist "%DSTROOT%\!SHORTDATE!\%%~nxF" (
                        echo Copy raw: %%~nxF
                        copy "%%F" "%DSTROOT%\!SHORTDATE!" >nul
                    ) else (
                        echo Skip raw: %%~nxF already exists.
                    )
                ) else (
                    echo Skip sorted: %%~nxF
                )
            )
        )
    )
)

echo Done rawdata: %NAME%
goto :eof


:BackupSleepReport
set "NAME=%~1"
set "SRC=%~2"
set "DST=%~3"

echo.
echo ----------------------------------------
echo Sleep Report Backup: %NAME%
echo SRC=%SRC%
echo DST=%DST%
echo ----------------------------------------

if not exist "%SRC%" (
    echo ERROR: Sleep report source not found. Skip %NAME%.
    goto :eof
)

if not exist "%DST%" (
    echo ERROR: Sleep report destination not found. Skip %NAME%.
    goto :eof
)

for /d %%D in ("%SRC%\*") do (
    for %%F in ("%%D\*睡眠报告.csv") do (
        if exist "%%F" (
            if not exist "%DST%\%%~nxF" (
                echo Copy report: %%~nxF
                copy "%%F" "%DST%" >nul
            ) else (
                echo Skip report: %%~nxF already exists.
            )
        )
    )
)

echo Done sleep report: %NAME%
goto :eof
