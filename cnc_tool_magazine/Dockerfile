FROM python:3.13-alpine

ARG BUILD_VERSION
ARG BUILD_ARCH

LABEL \
  io.hass.name="CNC Tool Magazine" \
  io.hass.description="Magazzino utensili CNC per Home Assistant" \
  io.hass.version="${BUILD_VERSION}" \
  io.hass.type="app" \
  io.hass.arch="${BUILD_ARCH}"

WORKDIR /app
COPY app.py /app/app.py
COPY www /app/www
COPY run.sh /run.sh
RUN pip install --no-cache-dir reportlab==4.4.9 && chmod a+x /run.sh

EXPOSE 8099
CMD ["/run.sh"]
