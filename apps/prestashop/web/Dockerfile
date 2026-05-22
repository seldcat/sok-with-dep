FROM prestashop/prestashop:1.7.5.1

COPY docker-php-ext-enable /usr/bin/

RUN sed -i s/deb.debian.org/archive.debian.org/g /etc/apt/sources.list \
    && sed -i 's|security.debian.org/debian-security|archive.debian.org/debian-security|g' /etc/apt/sources.list \
    && sed -i 's|httpredir.debian.org/debian|archive.debian.org/debian|g' /etc/apt/sources.list \
    && sed -i 's| stretch-updates| stretch|g' /etc/apt/sources.list \
    && apt -o Acquire::AllowInsecureRepositories=true update && apt install -y --allow-unauthenticated autoconf gcc make \
    && pecl install xdebug-2.6.1 \
    && docker-php-ext-enable xdebug \
    && echo 'auto_prepend_file = "/opt/xdebug.php"' >> $PHP_INI_DIR/conf.d/docker-php-ext-xdebug.ini

COPY xdebug.php /opt/xdebug.php
