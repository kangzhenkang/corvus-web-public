(function() {
  'use strict';

  angular
    .module('corvus')
    .controller('ProxyUpdateController', ProxyUpdateController);

  /* @ngInject */
  function ProxyUpdateController(proxyService, utils, notify, taskService) {
    var proxyUpdate = this;

    proxyUpdate.cancel = utils.cancel;
    proxyUpdate.commit = commit;

    var currentConf = angular.copy(proxyUpdate.config);

    function update(changes) {
      proxyUpdate.submitting = true;
      proxyService.update({
        clusterId: proxyUpdate.clusterId,
        host: proxyUpdate.host,
        config: changes
      }).then(function(response) {
        if (response.data.status === -1) {
          notify.warn(response.data.message);
        } else {
          utils.cancel();
          taskService.notifyTask({taskId: response.data.task_id});
        }
        proxyUpdate.submitting = false;
      }, function(err) {
        notify.warn(err.data.message);
        proxyUpdate.submitting = false;
      });
    }

    function commit() {
      var changes = {};
      var changed = false;
      angular.forEach(proxyUpdate.config, function(v, k) {
        if (currentConf[k] !== v) {
          changes[k] = v;
          changed = true;
        }
      });

      if (!changed) {
        notify.warn('没有改变');
        return;
      }

      changes.bind = currentConf.bind;
      update(changes);
    }
  }
})();
