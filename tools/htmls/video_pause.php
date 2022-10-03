<?php

$url = ""
if (isset($_GET["renderer_url"])) {
  $url = $_GET["renderer_url"];
  print $url;
}

$param = '<?xml version="1.0" encoding="utf-8"?>
          <s:Envelope s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/" xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
            <s:Body>
              <u:Pause xmlns:u="urn:schemas-upnp-org:service:AVTransport:1">
                <InstanceID>0</InstanceID>
              </u:Pause>
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
  "SOAPAction: \"urn:schemas-upnp-org:service:AVTransport:1#Pause\""
);
curl_setopt($ch, CURLOPT_HTTPHEADER, $headers);
curl_setopt($ch, CURLOPT_URL, $url);
$response = curl_exec($ch);

print $response

?>