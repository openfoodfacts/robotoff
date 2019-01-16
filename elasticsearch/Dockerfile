FROM elasticsearch:6.5.4

COPY gapless-stopfilter-plugin.zip /tmp/plugin.zip

ENV DISCOVERY_HOSTS ""
ENV MEMORY_LOCK true
ENV NODE_DATA true
ENV NODE_INGEST false
ENV NODE_MASTER true
ENV PUBLISH_HOST ""

RUN elasticsearch-plugin install --batch "file:///tmp/plugin.zip" \
&&  rm -rf /tmp/*
