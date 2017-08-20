let zmq = require('zeromq');
let uuid = require('uuid');

let pusher = zmq.socket('push');
let puller = zmq.socket('pull');

pusher.bindSync('tcp://127.0.0.1:3000');
console.log('Pusher started on port 3000');

puller.bindSync('tcp://127.0.0.1:3001');
console.log('Puller started on port 3001');

puller.on('message', function(msg){
  console.log(JSON.parse(msg.toString()));
});

let payload = {
  uuid: uuid.v4(),
  url: ['https://www.youtube.com/watch?v=lZWxMtXY1EE'],
  opts: {}
}
pusher.send(JSON.stringify(payload));
