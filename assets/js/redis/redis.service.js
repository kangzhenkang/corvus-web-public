(function() {
  'use strict';

  angular
    .module('corvus')
    .service('redisService', redisService);

  /* @ngInject */
  function redisService($http) {
    var redisService = this;

    redisService.deploy = deploy;
    redisService.getNodeInstances = getNodeInstances;
    redisService.getRedisArchives = getRedisArchives;
    redisService.isRedisInstalled = isRedisInstalled;
    redisService.installRedis = installRedis;

    function deploy(nodes) {
      return $http.post('/api/remote/agent/redis/deploy', nodes);
    }

    function getNodeInstances(host) {
      return $http.get('/api/node/instances', {
        params: {host: host}
      });
    }

    function getRedisArchives() {
      return $http.get('/api/redis/archive/names');
    }

    function isRedisInstalled() {
      return $http.get('/api/redis_package/installed');
    }

    function installRedis() {
      return $http.post('/api/redis_package');
    }
  }
})();
