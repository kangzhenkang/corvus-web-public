(function() {
  'use strict';

  angular
    .module('corvus')
    .controller('ProxyUpdateAllController', ProxyUpdateAllController);

  /* @ngInject */
  function ProxyUpdateAllController(utils, notify, proxyService, githubApi) {
    var manager = this;

    manager.cancel = utils.cancel;
    manager.submit = submit;
    manager.githubRelease = true;

    githubApi.getRelease(function(release) {
      manager.newVersion = release;
    });

    function submit() {
      if (!manager.newVersion) {
        notify.warn('填写一个版本');
        return;
      }
      if (manager.version && manager.version === manager.newVersion) {
        notify.warn('指定一个新版本再提交');
      }
      proxyService.updateAll(manager, manager.newVersion, manager.cluster,
                             manager.version, manager.registered,
        function(data) {
          notify.notice('任务已提交');
          utils.cancel();
        });
    }
  }
})();
