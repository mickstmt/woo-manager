# 🚀 Instrucciones de Deployment a Producción

**Fecha:** 2025-10-29
**Commit:** f6c760f
**Módulo:** Gestión Masiva de Precios + Optimizaciones de Rendimiento

---

## ⚠️ PRE-REQUISITOS

**CRÍTICO:** Estas operaciones afectarán la base de datos de producción. Ejecutar durante horario de bajo tráfico.

- ✅ Código probado completamente en LOCAL
- ✅ Modales funcionando correctamente
- ✅ Actualizaciones masivas probadas
- ✅ Puerto 5001 configurado y probado

---

## 📋 CHECKLIST DE DEPLOYMENT

### FASE 1: Preparación (10 minutos)

#### 1.1 Backup de Base de Datos ⚠️ OBLIGATORIO

```bash
# Conectar a servidor de producción
ssh usuario@tu-servidor-hostinger

# Crear directorio de backups si no existe
mkdir -p ~/backups

# Crear backup con timestamp
mysqldump -h localhost -u tu_usuario -p izis_db > ~/backups/izis_db_backup_$(date +%Y%m%d_%H%M%S).sql

# Verificar que se creó correctamente
ls -lh ~/backups/
```

**Tamaño esperado:** Varios MB (dependiendo de tu BD)

#### 1.2 Verificar Backup

```bash
# Ver primeras líneas del backup
head -n 20 ~/backups/izis_db_backup_*.sql

# Debe mostrar:
# -- MySQL dump ...
# -- Host: localhost ...
```

---

### FASE 2: Base de Datos (15-20 minutos)

#### 2.1 Crear Tabla de Historial de Precios

```bash
# Desde tu máquina local, subir el SQL al servidor
scp create_price_history_table.sql usuario@servidor:~/

# En el servidor, ejecutar
mysql -h localhost -u tu_usuario -p izis_db < ~/create_price_history_table.sql
```

**O usando cliente MySQL:**
1. Abrir [create_price_history_table.sql](create_price_history_table.sql)
2. Cambiar línea 12: `USE izis_db;` (verificar nombre de BD)
3. Ejecutar en tu cliente MySQL de Hostinger

**Verificar que se creó:**
```sql
SHOW TABLES LIKE 'woo_price_history';
DESCRIBE woo_price_history;
```

#### 2.2 Crear Índices de Optimización (SI AÚN NO SE CREARON)

```bash
# Subir archivo de índices
scp create_indexes.sql usuario@servidor:~/

# Ejecutar (esto puede tardar 5-15 minutos)
mysql -h localhost -u tu_usuario -p izis_db < ~/create_indexes.sql
```

**Verificar índices creados:**
```sql
-- Verificar índices en wpyz_postmeta
SHOW INDEX FROM wpyz_postmeta;

-- Deberías ver: idx_meta_key_value
-- Verificar índices en wpyz_posts
SHOW INDEX FROM wpyz_posts;

-- Deberías ver: idx_posts_type_status, idx_posts_parent, idx_posts_date
```

---

### FASE 3: Código de Aplicación (5 minutos)

#### 3.1 Push de Cambios

```bash
# Desde tu máquina local
git push origin main
```

#### 3.2 Actualizar Servidor

```bash
# Conectar al servidor
ssh usuario@tu-servidor-hostinger

# Navegar al directorio del proyecto
cd /ruta/a/woocommerce-manager

# Pull de cambios
git pull origin main

# Verificar que se descargaron los archivos
git log -1 --oneline
# Debe mostrar: f6c760f Implementar módulo de gestión masiva de precios...
```

#### 3.3 Instalar Dependencias

```bash
# Activar entorno virtual (si usas uno)
source venv/bin/activate  # O el comando que uses

# Instalar Flask-Caching
pip install -r requirements.txt

# Verificar instalación
pip list | grep Flask-Caching
# Debe mostrar: Flask-Caching  2.1.0
```

---

### FASE 4: Reinicio de Aplicación (2 minutos)

#### 4.1 Reiniciar Servicio

**Opción A: Si usas systemd**
```bash
sudo systemctl restart woocommerce-manager
sudo systemctl status woocommerce-manager
```

**Opción B: Si usas supervisor**
```bash
sudo supervisorctl restart woocommerce-manager
sudo supervisorctl status woocommerce-manager
```

**Opción C: Si usas PM2**
```bash
pm2 restart woocommerce-manager
pm2 status
```

**Opción D: Si usas screen/tmux**
```bash
# Detener proceso actual (Ctrl+C en la sesión)
# Reiniciar aplicación
python run.py
```

#### 4.2 Verificar que Inició Correctamente

```bash
# Ver logs del servicio
sudo journalctl -u woocommerce-manager -f -n 50

# O si usas logs en archivo
tail -f /ruta/a/logs/woocommerce.log

# Deberías ver:
# ========================
# 🚀 Iniciando WooCommerce Manager
# ========================
# 🌍 Ambiente: PRODUCTION
# 🗄️  Base de datos: izis_db
# ...
```

---

### FASE 5: Verificación (10 minutos)

#### 5.1 Tests Funcionales

1. **Abrir aplicación en navegador:**
   ```
   https://tu-dominio.com
   ```

2. **Probar módulo de Precios:**
   - Ir a `/prices`
   - Buscar un producto por SKU
   - Verificar que carga en < 1 segundo
   - Hacer clic en "Incrementar %"
   - Verificar que modal se abre correctamente
   - Seleccionar 2-3 productos
   - Aplicar incremento del 10%
   - Verificar que precios se actualizaron

3. **Probar otros módulos:**
   - Ir a `/products` → Debe cargar rápido (< 0.5s)
   - Ir a `/stock` → Buscar un SKU → Debe ser rápido

4. **Verificar Historial:**
   - En `/prices`, hacer clic en "📊" de un producto actualizado
   - Verificar que muestra el cambio de precio
   - Verificar fecha y usuario

#### 5.2 Verificar Base de Datos

```sql
-- Verificar que se guardó el historial
SELECT * FROM woo_price_history ORDER BY created_at DESC LIMIT 5;

-- Verificar productos actualizados
SELECT post_id, meta_key, meta_value
FROM wpyz_postmeta
WHERE post_id IN (SELECT product_id FROM woo_price_history ORDER BY created_at DESC LIMIT 5)
  AND meta_key IN ('_regular_price', '_sale_price', '_price');
```

#### 5.3 Monitoreo de Performance

```bash
# Monitorear uso de CPU/memoria
top

# Monitorear logs en tiempo real
tail -f /ruta/a/logs/woocommerce.log

# Buscar errores
grep -i error /ruta/a/logs/woocommerce.log
```

---

## 🆘 ROLLBACK (Si algo sale mal)

### Si hay problemas con la aplicación:

```bash
# Volver al commit anterior
git reset --hard HEAD~1
git push origin main --force

# Reiniciar servicio
sudo systemctl restart woocommerce-manager
```

### Si hay problemas con la BD:

```bash
# Restaurar backup
mysql -h localhost -u tu_usuario -p izis_db < ~/backups/izis_db_backup_TIMESTAMP.sql

# Borrar tabla de historial si es necesario
mysql -h localhost -u tu_usuario -p izis_db -e "DROP TABLE IF EXISTS woo_price_history;"
```

---

## 📊 Monitoreo Post-Deployment (24-48 horas)

### Métricas a vigilar:

1. **Tiempos de respuesta:**
   - `/products` → Objetivo: < 500ms
   - `/stock` → Objetivo: < 300ms
   - `/prices` → Objetivo: < 500ms

2. **Uso de recursos:**
   - CPU: < 30% en promedio
   - Memoria: < 500MB
   - Conexiones DB: < 10 simultáneas

3. **Errores:**
   ```bash
   # Revisar logs cada 6 horas
   grep -i error /ruta/a/logs/woocommerce.log | tail -20
   ```

---

## 🎯 Nuevas Funcionalidades Disponibles

### Para Usuarios:

1. **Módulo de Precios** (`/prices`)
   - Búsqueda por SKU, nombre, categoría
   - Actualización inline de precios
   - 4 modos de actualización masiva:
     - Incrementar % (ej: subir 10% todos los productos)
     - Descontar % (ej: bajar 15% en ofertas)
     - Precio fijo (ej: poner $100 a varios productos)
     - Quitar ofertas (eliminar sale_price de productos)
   - Historial de cambios con auditoría

2. **Mejoras de Performance:**
   - Todas las páginas cargan 20-100x más rápido
   - Búsquedas instantáneas con caché
   - Menor uso de base de datos

---

## 📝 Configuración Post-Deployment (Opcional)

### Optimización de Caché con Redis (Recomendado para producción)

Si quieres máximo rendimiento:

```bash
# Instalar Redis
pip install redis

# Modificar config.py - Clase ProductionConfig:
CACHE_TYPE = 'RedisCache'
CACHE_REDIS_HOST = 'localhost'
CACHE_REDIS_PORT = 6379
CACHE_REDIS_DB = 0
CACHE_DEFAULT_TIMEOUT = 300
```

**Beneficios:**
- Caché persistente (no se pierde al reiniciar)
- ~100x más rápido que SimpleCache
- Soporta múltiples workers

---

## ✅ CHECKLIST FINAL

### Pre-Deployment
- [ ] Backup de BD creado y verificado
- [ ] Código probado en local
- [ ] Commit f6c760f creado

### Deployment
- [ ] Tabla `woo_price_history` creada
- [ ] Índices de BD creados (si no estaban)
- [ ] Código actualizado en servidor
- [ ] Flask-Caching instalado
- [ ] Servicio reiniciado correctamente

### Verificación
- [ ] Aplicación inicia sin errores
- [ ] Módulo `/prices` funciona
- [ ] Modales se abren correctamente
- [ ] Actualización masiva funciona
- [ ] Historial se guarda en BD
- [ ] Performance mejorado (< 500ms)

### Monitoreo
- [ ] Logs monitoreados por 1 hora
- [ ] Sin errores críticos
- [ ] Performance estable
- [ ] Usuarios notificados de nuevas funcionalidades

---

## 🔗 Archivos de Referencia

- [OPTIMIZACIONES.md](OPTIMIZACIONES.md) - Documentación técnica completa
- [create_price_history_table.sql](create_price_history_table.sql) - Script SQL de tabla
- [create_indexes.sql](create_indexes.sql) - Script de índices
- [app/routes/prices.py](app/routes/prices.py) - Backend del módulo
- [app/templates/prices.html](app/templates/prices.html) - Frontend del módulo

---

## 📞 Soporte

Si encuentras algún problema durante el deployment:

1. Revisar logs del servicio
2. Verificar que BD tiene la tabla `woo_price_history`
3. Verificar que Flask-Caching está instalado
4. Consultar [OPTIMIZACIONES.md](OPTIMIZACIONES.md) sección Troubleshooting

---

**¡Deployment exitoso!** 🎉

El sistema ahora cuenta con gestión masiva de precios y está optimizado para alto rendimiento.
