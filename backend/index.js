let zmq = require('zeromq');
let uuid = require('uuid');
let express = require('express');

// SETUP

let app = express();
let server = require('http').Server(app);
var io = require('socket.io')(server);

let pusher = zmq.socket('push');
let puller = zmq.socket('pull');

let pending_tasks = {};

function launch() {
  pusher.bindSync('tcp://127.0.0.1:3000');
  puller.bindSync('tcp://127.0.0.1:3001');
  app.use(express.static('static'));
  app.set('view engine', 'pug');
  server.listen(3002);

  console.log('Application is listening (3000 pusher, 3001 puller, 3002 http)');
}

// ROUTES
app.get('/', function (req, res) {
  res.render('index');
});

io.on('connection', function (socket) {
  socket.on('download', function (data) {
    let payload = {
      uuid: uuid.v4(),
      url: data.url,
      opts: {}
    };
    console.log('['+payload.uuid+'] received a download request for '+data.url);
    pending_tasks[payload.uuid] = {socket: socket, payload: payload};
    setTimeout(function() {
      delete pending_tasks[payload.uuid];
    }, 5 * 3600 * 1000); // 5 hours
    pusher.send(JSON.stringify(payload));
  });
});

puller.on('message', function(msg) {
  msg = JSON.parse(msg.toString());
  console.log('['+msg.uuid+'] received a '+msg.status+' response');

  if (msg.data && msg.data._filename) {
    msg.data.download_link = "http://archiviste.deuxfleurs.fr/downloads/" + msg.data._filename;
  }

  socket = pending_tasks[msg.uuid].socket;
  socket.emit('tracking', msg);
});

// MAIN
launch();

