<?php
 

  $ip = gethostbyaddr('192.168.5.25');
  $port = 6722; // если UDP то порт 6723
 
  $socket = socket_create(AF_INET, SOCK_STREAM, SOL_TCP);
  if($socket and socket_connect($socket, $ip, $port)){
    $cmd = "21";
    //$cmd = $_GET['cmd'] . "*";  // будет возвращено в начальное положение через 0.5 сек
    //$cmd = $_GET['cmd'] . ":3";  // будет возвращено в начальное положение через 3 сек
    socket_write($socket, $cmd, strlen($cmd));
//    echo socket_read($socket, 8);
    socket_close($socket);
  }else{
    echo "Error socket:" . socket_strerror(socket_last_error());
  }

 
 
?>
