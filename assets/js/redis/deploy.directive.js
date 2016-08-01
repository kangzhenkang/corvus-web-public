(function() {
  'use strict';

  angular
    .module('corvus')
    .directive('cvRedisDeploy', cvRedisDeploy);

  /* @ngInject */
  function cvRedisDeploy() {
    return {
      controller: RedisDeployController,
      controllerAs: 'redisDeploy',
      restrict: 'A',
    };
  }

  /* @ngInject */
  function RedisDeployController($mdDialog, redisService, utils, notify, taskService) {
    var redisDeploy = this;

    redisDeploy.entries = [{index: 1}];
    redisDeploy.cancel = utils.cancel;
    redisDeploy.commit = commit;
    redisDeploy.addEntry = addEntry;
    redisDeploy.deleteEntry = deleteEntry;

    redisDeploy.activate = activate;
    redisDeploy.getNodeInstances = getNodeInstances;
    redisDeploy.installRedis = installRedis;

    redisDeploy.node = {};
    redisDeploy.archives = [];
    redisDeploy.redisInstalled = true;

    redisService.getRedisArchives()
      .then(function(response) {
        if (response.data.status == -1) {
          notify.warn(response.data.message);
        } else {
          redisDeploy.archives = response.data.archives;
        }
      }, function(err) {
        notify.warn(err.data.message);
      });

    updateRedisInstalled();

    function activate() {
      $mdDialog.show({
        templateUrl: '/static/template/redis/deploy.html',
        controller: RedisDeployController,
        controllerAs: 'redisDeploy',
      });
    }

    function addEntry() {
      var length = redisDeploy.entries.length;
      redisDeploy.entries.unshift({index: length});
    }

    function deleteEntry(entry) {
      utils.remove(redisDeploy.entries, entry);
    }

    function commit() {
      if (!redisDeploy.selectedArchive) {
        notify.warn('redis版本未选择')
        return;
      }

      var nodes = [];
      for (var i in redisDeploy.entries) {
        var v = redisDeploy.entries[i];
        if (v.host && v.port && v.maxmemory) {
          var addrs = utils.parseAddress(v.host, v.port);
          if (addrs.length <= 0) {
            notify.warn('节点信息填写错误: ' + v.host + ', ' + v.port);
            return;
          }
          addrs.map(function(n) {
            n.maxmemory = v.maxmemory;
            n.persistence = Boolean(v.persistence);
            n.archive = redisDeploy.selectedArchive;
          });
          nodes = nodes.concat(addrs);
        } else {
          notify.warn('未填写完整');
          return;
        }
      }
      var addrs = nodes.map(function(n) {
        return {host: n.host, port: n.port};
      });
      if (utils.uniqueAddress(addrs).length != nodes.length) {
        notify.warn('存在重复节点');
        return;
      }
      if (nodes.length <= 0) {
        notify.warn('请输入需要启动的redis节点');
        return;
      }

      redisDeploy.submitting = true;
      redisService.deploy(nodes)
        .then(function(response) {
          if (response.data.status == -1) {
            notify.warn(response.data.message);
          } else {
            notify.notice('已成功添加任务');
            utils.cancel();
          }
          redisDeploy.submitting = false;
        }, function(err) {
          notify.warn(err.data.message);
          redisDeploy.submitting = false;
        });
    }

    function getNodeInstances(host) {
      redisService.getNodeInstances(host)
        .then(function(response) {
          if (response.data.status == -1) {
            notify.warn(response.data.message);
          } else {
            redisDeploy.node[host] = {
              instances_num: response.data.instances_num,
              mem_used_sum: utils.formatBytes(response.data.mem_used_sum),
              max_mem_sum: utils.formatBytes(response.data.max_mem_sum),
              total_mem: utils.formatBytes(response.data.total_mem)
            };
          }
        }, function(err) {
          notify.warn(err.data.message);
        })
    }

    function installRedis() {
      redisService.installRedis()
        .then(function(response) {
          if (response.data.status == -1) {
            notify.warn(response.data.message);
          } else {
            var taskId = response.data.task_id;
            taskService.notifyTask({taskId: taskId});
            utils.cancel();
          }
        }, function(err) {
          notify.warn(err.data.message);
        })
    }

    function updateRedisInstalled() {
      redisService.isRedisInstalled()
        .then(function(response) {
          if (response.data.status == -1) {
            notify.warn(response.data.message);
          } else {
            redisDeploy.redisInstalled = response.data.installed;
          }
        }, function(err) {
          notify.warn(err.data.message);
        })
    }
  }
})();
