<!DOCTYPE html>
<html lang="ja">
<head>
<title>index</title>
<meta charset="UTF-8">
<script src="//cdnjs.cloudflare.com/ajax/libs/socket.io/2.2.0/socket.io.js" integrity="sha256-yr4fRk/GU1ehYJPAs8P4JlTgu0Hdsp4ZKrx8bDEDC3I=" crossorigin="anonymous"></script>
</head>
<body>
<div>ロボットの状態 <span id="status"></span></div>
<div>
    <label><input type="radio" name="pen" id="pen_up" checked>ペンを上げる</label>
    <label><input type="radio" name="pen" id="pen_down">ペンを下げる</label>
</div>
<div>
    <canvas id="canvas" style="border:solid black 1px"></canvas>
    <canvas id="cursor" style="display: none"></canvas>
</div>
<div>メッセージ <input type="text" id="message" size="30" maxlength="20"><input type="button" id="sendtext" value="書く"></div>
<br>
<br>
<br>
<div>
    <input type="button" id="align" value="原点復帰">
    <input type="button" id="clear" value="クリア（紙交換）">
</div>

<script type="text/javascript">

    //BASE64デコード
    var Base64a = {
        decode: (function(i, tbl) {
            for(i=0,tbl={61:64,47:63,43:62}; i<62; i++) {tbl[i<26?i+65:(i<52?i+71:i-4)]=i;} //A-Za-z0-9+/=
            return function(str) {
                var j, len, arr, buf;
                if (!str || !str.length) {return [];}
                for(i=0,len=str.length,arr=[],buf=[]; i<len; i+=4) { //6,2+4,4+2,6
                    for(j=0; j<4; j++) {buf[j] = tbl[str.charCodeAt(i+j)||0];}
                    arr.push(
                        buf[0]<<2|(buf[1]&63)>>>4,
                        (buf[1]&15)<<4|(buf[2]&63)>>>2,
                        (buf[2]&3)<<6|buf[3]&63
                    );
                }
                if (buf[3]===64) {arr.pop();if (buf[2]===64) {arr.pop();}}
                return arr;
            };
        }())
    };

    //キャンバス上のマウス座標を取得
    function getMousePosition(canvas, evt) {
        var rect = canvas.getBoundingClientRect();
        return {
            x: evt.clientX - rect.left,
            y: evt.clientY - rect.top,
            lb: evt.buttons & 1
        };
    }

    //SocketIO
    var socket = io('<?php echo $_SERVER['SERVER_ADDR']; ?>:5000');

    window.onload = function(){

        //キャンバスを操作する変数
        var canvas = document.getElementById('canvas');
        var context = canvas.getContext('2d');
        var image_data; //更新頻度が多いのでベースの画像データを保持
        var canvas_cx = 0;
        var canvas_cy = 0;

        //ペンの位置を表す画像を保持
        var cursor = document.getElementById('cursor');
        var cursor_size = 7;

        //ロボットの状態を表示するspan
        var status = document.getElementById("status");
        var busy = false;

        //現在のペンの位置を保持
        var current_x = 0;
        var current_y = 0;

        //ボタン
        var pendown_button = document.getElementById("pen_down");
        var penup_button = document.getElementById("pen_up");
        var sendtext_button = document.getElementById("sendtext");
        var align_button = document.getElementById("align");
        var clear_button = document.getElementById("clear");


        //初期化コード
        init();
        function init() {

            //カーソル作成
            var ctx = cursor.getContext('2d');
            var image_data = ctx.createImageData(cursor_size, cursor_size);
            var a = image_data.data;
            var n = cursor_size * cursor_size;
            var di = 3;
            while(n-- > 0) {
                a[di] = 0;//背景透明
                di += 4;
            }
            //カーソルの×印を描画
            ctx.putImageData(image_data ,0 ,0);
            ctx.beginPath();
            ctx.strokeStyle = 'rgba(255, 0, 0, 0.5)';
            ctx.moveTo(0, 0);
            ctx.lineTo(cursor_size - 1, cursor_size - 1);
            ctx.moveTo(0, cursor_size - 1);
            ctx.lineTo(cursor_size - 1, 0);
            ctx.closePath();
            ctx.stroke();
        }

        socket.on('json', function(json) {
            //console.log(json_string);
            //json = JSON.parse(json_string);

            if (json.image != undefined) {
                //ビットデータの復元(window.btoa()ではダメ)
                var bs = Base64a.decode(json.image);

                //キャンバスイメージデータの取得
                image_data = context.createImageData(json.width, json.height);

                //データ変換 RGB=>RGBA
                var a = image_data.data;
                var n = json.width * json.height;
                var si = 0;
                var di = 0;
                while(n-- > 0) {
                    a[di++] = bs[si++];
                    a[di++] = bs[si++];
                    a[di++] = bs[si++];
                    a[di++] = 255;
                }

                //キャンバスに反映。image_dataは保持しておく
                context.putImageData(image_data ,0 ,0);
                canvas.width = json.width;
                canvas.height = json.height;
                canvas_cx = json.cx;
                canvas_cy = json.cy;

                console.log('image ' + json.width + 'x' + json.height + ' center(' + canvas_cx + ',' + canvas_cy + ')');
            } else {
                console.log(JSON.stringify(json));
            }
            if (json.status != undefined) {
                busy = (json.status == "ビジー");
                status.innerHTML = json.status;

                //BUSYでボタンを無効化
                var disabled = busy ? "disabled" : "";
                pendown_button.disabled = disabled;
                penup_button.disabled = disabled;
                sendtext_button.disabled = disabled;
                align_button.disabled = disabled;
                clear_button.disabled = disabled;
            }
            if (json.pen != undefined) {
                //document.getElementsByName("pen")[json.pen].checked = true; //json.pen = 0 or 1
            }
            if (json.x != undefined) {
                context.putImageData(image_data ,0 ,0);         //主画像復帰
                cs = parseInt(cursor_size / 2);
                context.drawImage(cursor, json.x + canvas_cx - cs, json.y + canvas_cy - cs);  //カーソル合成
                current_x = json.x;
                current_y = json.y;
            }
            if (json.x1 != undefined) {
                context.putImageData(image_data ,0 ,0);         //主画像復帰
                context.beginPath();
                context.moveTo(json.x1 + canvas_cx, json.y1 + canvas_cy);
                context.lineTo(json.x2 + canvas_cx, json.y2 + canvas_cy);
                context.closePath();
                context.stroke();
                image_data = context.getImageData(0, 0, image_data.width, image_data.height); //ビットマップを保存
                context.drawImage(cursor, json.x2 + canvas_cx - 3, json.y2 + canvas_cy - 3);  //カーソル合成
                current_x = json.x2;
                current_y = json.y2;
            }
        });

        //「ペンを下げる」ラジオボタンが押された
        //(プログラムによる変更は反応しない)
        pendown_button.addEventListener('change', function () {
            //socket.emit('json', {pen: 1});
        });

        //「ペンを上げる」ラジオボタンが押された
        //(プログラムによる変更は反応しない)
        penup_button.addEventListener('change', function () {
            //socket.emit('json', {pen: 0});
        });

        //マウスボタンが押された
        canvas.addEventListener('mousedown', function (evt) {
            if (busy) return;
            var pos = getMousePosition(canvas, evt);    //座標取得
            moveto(pos.x, pos.y, true); //移動のみ
        }, false);

        //マウスが移動した
        canvas.addEventListener('mousemove', function (evt) {
            if (busy) return;
            var pos = getMousePosition(canvas, evt);    //座標取得
            if (pos.lb == 0) return;
            moveto(pos.x, pos.y, false);
        }, false);

        //マウスボタンが離された
        canvas.addEventListener('mouseup', function (evt) {
            if (busy) return;
            var pos = getMousePosition(canvas, evt);    //座標取得
            if (current_x != pos.x || current_y != pos.y) {
                moveto(pos.x, pos.y, false);
            }
        }, false);

        function moveto(x, y, moveOnly) {
            var rx = x - canvas_cx; //ロボット座標
            var ry = y - canvas_cy;

            if (!moveOnly && pendown_button.checked) {
                //ペンが下がっている
                socket.emit('json', {x1: current_x, y1: current_y, x2: rx, y2: ry});
                context.putImageData(image_data ,0 ,0);         //主画像復帰
                //線を引く
                context.beginPath();
                context.moveTo(current_x + canvas_cx, current_y + canvas_cy);
                context.lineTo(x, y);
                context.closePath();
                context.stroke();
                image_data = context.getImageData(0, 0, image_data.width, image_data.height); //ビットマップを保存

            } else {
                //ペンが上がっている
                socket.emit('json', {x: rx, y: ry});
                context.putImageData(image_data ,0 ,0);         //主画像復帰
            }
            cs = parseInt(cursor_size / 2);
            context.drawImage(cursor, x - cs, y - cs);  //カーソル合成
            current_x = rx;
            current_y = ry;
        }



        //（文字を）書く
        sendtext_button.addEventListener('click', function () {
            var tbox = document.getElementById("message");
            var text = tbox.value;
            socket.emit('json', {text: text});
            tbox.value = "";
        });

        //原点復帰
        align_button.addEventListener('click', function () {
            socket.emit('json', {align: 0});
        });

        //クリア（紙交換）
        clear_button.addEventListener('click', function () {
            socket.emit('json', {clear: 0});
        });
    }
</script>

</body>
</html>
