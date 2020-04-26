<?php
require_once './vendor/autoload.php';
require_once './helperFunctions.php';

$http = new Swoole\HTTP\Server("0.0.0.0", 80);
$pathToTADmuffin = realpath(__DIR__.'/workdir').'/TADmuffin.py';
$pathToUSMbin = realpath(__DIR__.'/workdir').'/usm.bin';

$loader = new \Twig\Loader\FilesystemLoader('./views');
$twig = new \Twig\Environment($loader);

$http->on('start', function ($server) {
    echo "Slottool http server is started at http://0.0.0.0:80\n";
});

$http->on('request', function ($request, $response) use ($twig, $pathToTADmuffin) {
    if (isset($request->get['keyY']) && 
        ctype_xdigit($request->get['keyY']) && strlen($request->get['keyY']) == 32
        ) {
        $keyY = $request->get['keyY'];
        $tempOutputFileName = tempnam(sys_get_temp_dir(), 'slottool');
        $tempOutputFolder = tempdir(sys_get_temp_dir(), 'slottool');
        $output = shell_exec('python '.$pathToTADmuffin.' '.$keyY.' '.$tempOutputFolder.'/ '.$tempOutputFileName.' 2>&1');
        $outputLines = explode("\n", $output);

        $rebuildSuccess = false;
        foreach($outputLines as $currentOutputLine) {
            if ($currentOutputLine == "Rebuilt to " . $tempOutputFileName) 
                $rebuildSuccess = true;
        }

        if (!$rebuildSuccess) {
            $response->header("Content-Type", "text/html");
            $response->end("<h1>Error while generating your unSAFE_MODE-bb3 files!</h1><pre>" . $output . "</pre>");
            return;
        }

        $zip = new \ZipArchive();
        $tempZipFilename = tempnam(sys_get_temp_dir(), 'slottool');
        $zip->open($tempZipFilename, \ZipArchive::CREATE);
        $zip->addFile($tempOutputFileName, 'F00D43D5.bin');
        $zip->addFile($pathToUSMbin, 'usm.bin');
        $zip->close();
        $zipContent = file_get_contents($tempZipFilename);
        unlink($tempZipFilename);
        unlink($tempOutputFileName);
        rmdir_recursive($tempOutputFolder);

        $response->header('Content-Disposition','attachment; filename="unSAFE_MODE-bb3.zip"');
        $response->header("Content-Type", "text/plain");
        $response->header("Content-Length", strlen($zipContent));
        $response->end($zipContent);
        return;
    }

    $response->header("Content-Type", "text/html");
    $response->end($twig->render('index.html'));
});

$http->start();
