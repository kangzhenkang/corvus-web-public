(function() {
  'use strict';

  angular
    .module('corvus')
    .service('utils', Utils);

  /* @ngInject */
  function Utils($mdDialog) {
    this.formatBytes = formatBytes;
    this.formatPercent = formatPercent;
    this.getMemoryClass = getMemoryClass;
    this.getAddresses = getAddresses;
    this.parseAddress = parseAddress;
    this.uniqueAddress = uniqueAddress;
    this.remove = remove;
    this.confirm = confirm;
    this.cancel = cancel;
    this.formatDate = formatDate;

    function pad(v, width) {
      while (v.length < width) {
        v = '0' + v;
      }
      return v;
    }

    function formatDate(date) {
      date = new Date(date);
      var year  = date.getFullYear(),
          month = pad(String(date.getMonth() + 1), 2),
          day   = pad(String(date.getDate()), 2),
          h     = pad(String(date.getHours()), 2),
          min   = pad(String(date.getMinutes()), 2),
          s     = pad(String(date.getSeconds()), 2);
      return year + '-' + month + '-' + day + ' ' + h + ':' + min + ':' + s;
    }

    function formatBytes(bytes) {
      if(bytes === 0) {
        return '0b';
      }

      var k = 1024;
      var sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
      var i = Math.floor(Math.log(bytes) / Math.log(k));
      return Number((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    function formatPercent(x, y) {
      return Number((x / y * 100).toFixed(2)) + '%';
    }

    function getMemoryClass(x, y) {
      var delta = x / y;
      if (delta > 0.9) {
        return 'label-red';
      } else if (delta > 0.8) {
        return 'label-yellow';
      } else {
        return 'label-green';
      }
    }

    function uniqueAddress(arr) {
      var tags = [];
      return arr.reduce(function(a, b) {
        var tag = b.host + ":" + b.port;
        if (tags.indexOf(tag) < 0) {
          a.push(b);
          tags.push(tag);
        }
        return a;
      }, []);
    }

    function parseAddress(host, spec) {
      var addresses = [];
      var parts = spec.split(',');
      angular.forEach(parts, function(v) {
        v = v.trim();
        var range = v.split('-');
        switch (range.length) {
          case 1:
            var port = parseInt(range[0]);
            if (!port) {
              return [];
            }
            addresses.push({host: host, port: port});
            break;
          case 2:
            var start = parseInt(range[0]);
            var end = parseInt(range[1]);
            if (!start || !end || end < start) {
              return [];
            }
            for (var i = start; i <= end; i++) {
              addresses.push({host: host, port: i});
            }
            break;
          default:
            return [];
        }
      });
      return addresses;
    }

    function getAddresses(arr) {
      var nodes = [];
      angular.forEach(arr, function(v) {
        if (v.host && v.port) {
          var addrs = parseAddress(v.host, v.port);
          if (addrs.length <= 0) {
            notify.warn('节点信息填写错误: ' + v.host + ', ' + v.port);
            return;
          }
          nodes = nodes.concat(addrs);
        }
      });
      return uniqueAddress(nodes);
    }

    function remove(arr, item) {
      var idx = arr.indexOf(item);
      if (idx >= 0) {
        arr.splice(idx, 1);
      }
    }

    function confirm(title, content) {
      return $mdDialog
        .confirm()
        .title(title)
        .textContent(content)
        .cancel('取消')
        .ok('确定');
    }

    function cancel() {
      $mdDialog.cancel();
    }
  }
})();
