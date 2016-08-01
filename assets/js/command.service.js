(function() {
  'use strict';

  angular
    .module('corvus')
    .service('cmdService', CmdService);

  /* @ngInject */
  function CmdService($http, $mdDialog) {
    this.executeCommand = executeCommand;
    this.popup = popup;

    function executeCommand(host, port, command) {
      return $http.get('/api/command/' + host + '/' + port + '/' + command);
    }

    function popup(item) {
      $mdDialog.show({
        templateUrl: '/static/template/command.html',
        controller: 'CommandController',
        controllerAs: 'cmd',
        bindToController: true,
        locals: {
          host: item.host,
          port: item.port
        },
      });
    }
  }
})();
