<?php

$video_url = "test";
if (isset($_GET["url"])) {
  $video_url = $_GET["url"];
  print $video_url;
}

$url = ""
if (isset($_GET["renderer_url"])) {
  $url = $_GET["renderer_url"];
  print $url;
}

$format = '<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
           <s:Body>
             <u:SetNextAVTransportURI xmlns:u="urn:schemas-upnp-org:service:AVTransport:1">
               <InstanceID>0</InstanceID>
               <NextURI>%s</NextURI>
               <NextURIMetaData></NextURIMetaData>
             </u:SetNextAVTransportURI>
           </s:Body>
         </s:Envelope>';
$param = sprintf($format, $video_url);

print $param;

$ch = curl_init();
curl_setopt($ch, CURLOPT_POSTFIELDS, $param);
curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, 0);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
curl_setopt($ch, CURLOPT_HEADER, 1);
curl_setopt($ch, CURLOPT_POST, true);

$headers = array(
  "Content-Type: text/xml; charset=utf-8",
  "SOAPAction: \"urn:schemas-upnp-org:service:AVTransport:1#SetAVTransportURI\""
);
curl_setopt($ch, CURLOPT_HTTPHEADER, $headers);
curl_setopt($ch, CURLOPT_URL, $url);
$response = curl_exec($ch);

print $response;

$param = '<?xml version="1.0" encoding="utf-8"?>
          <s:Envelope s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/" xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
            <s:Body>
              <u:Play xmlns:u="urn:schemas-upnp-org:service:AVTransport:1">
                <InstanceID>0</InstanceID>
                <Speed>1</Speed>
              </u:Play>
            </s:Body>
          </s:Envelope>';

$ch = curl_init();
curl_setopt($ch, CURLOPT_POSTFIELDS, $param);
curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, 0);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
curl_setopt($ch, CURLOPT_HEADER, 1);
curl_setopt($ch, CURLOPT_POST, true);

$headers = array(
  "Content-Type: text/xml; charset=utf-8",
  "SOAPAction: \"urn:schemas-upnp-org:service:AVTransport:1#Play\""
);
curl_setopt($ch, CURLOPT_HTTPHEADER, $headers);
curl_setopt($ch, CURLOPT_URL, $url);
$response = curl_exec($ch);

print $response
?>