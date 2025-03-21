<?php
 
if(@$_GET['cmd']){
  $ip = gethostbyaddr('192.168.1.100');
  $port = 6722; // если UDP то порт 6723
 
  $socket = socket_create(AF_INET, SOCK_STREAM, SOL_TCP);
  if($socket and socket_connect($socket, $ip, $port)){
    $cmd = $_GET['cmd'];
    //$cmd = $_GET['cmd'] . "*";  // будет возвращено в начальное положение через 0.5 сек
    //$cmd = $_GET['cmd'] . ":3";  // будет возвращено в начальное положение через 3 сек
    socket_write($socket, $cmd, strlen($cmd));
    echo socket_read($socket, 8);
    socket_close($socket);
  }else{
    echo "Error socket:" . socket_strerror(socket_last_error());
  }
}
 
 
?>
<a href="?cmd=11">Первое реле ВКЛЮЧИТЬ</a><br>
<a href="?cmd=21">Первое реле ВЫКЛЮЧИТЬ</a><br>
<a href="?cmd=12">Второе реле ВКЛЮЧИТЬ</a><br>
<a href="?cmd=22">Второе реле ВЫЛЮЧИТЬ</a>

