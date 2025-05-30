import React, { useState, useEffect } from 'react';
import ReactDOM from 'react-dom/client';

// ... (SVG Icons and VMStatus type - estas partes no cambian) ...

// --- Types ---
type VMStatus = 'Running' | 'Stopped' | 'Provisioning';

interface VM {
    id: string;
    name: string;
    zoneRegion: string;
    ipExternal: string | null;
    ipInternal: string;
    machineType: string;
    status: VMStatus;
}

// --- CONFIGURACIÓN DEL BACKEND ---
// Define la URL base de tu backend.
// Para desarrollo local, será la dirección donde se ejecuta Uvicorn.
// Para producción en Cloud Run, será la URL de tu servicio de Cloud Run.
const API_BASE_URL = 'http://localhost:8000/api'; 
// En producción, esto cambiará a la URL de tu servicio Cloud Run (ej. 'https://tu-servicio-backend-xxxxxx-ew.a.run.app/api')


// --- Components ---
// ... (Header, FilterBar, VMCard - estas partes no cambian, solo se usarán los datos de la API) ...

const App: React.FC = () => {
    const [vms, setVms] = useState<VM[]>([]); // Estado inicial de VMs vacío
    const [searchTerm, setSearchTerm] = useState('');
    const [statusFilter, setStatusFilter] = useState('Todos');
    const [zoneFilter, setZoneFilter] = useState('Todas');
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null); // Para manejar errores de la API

    // Obtener todas las zonas únicas de las VMs actuales (para el filtro de zona)
    // Esto se recalcula cada vez que 'vms' cambia
    const allZones = Array.from(new Set(vms.map(vm => vm.zoneRegion))).sort();

    // Función para obtener las VMs del backend
    const fetchVms = async () => {
        setIsLoading(true);
        setError(null); // Limpia errores anteriores
        try {
            const response = await fetch(`${API_BASE_URL}/vms`);
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Error al obtener las VMs del backend.');
            }
            const data: VM[] = await response.json();
            setVms(data);
        } catch (err: any) {
            console.error('Error al obtener VMs:', err);
            setError(err.message || 'Error de red o del servidor al obtener VMs.');
            setVms([]); // Limpia las VMs en caso de error
        } finally {
            setIsLoading(false);
        }
    };

    // Efecto para cargar las VMs al inicio de la aplicación
    useEffect(() => {
        fetchVms();
    }, []); // El array vacío asegura que se ejecute solo una vez al montar

    // Función para encender/apagar una VM
    const handleTogglePower = async (vmName: string, zone: string, currentStatus: VMStatus) => {
        setIsLoading(true);
        setError(null);
        try {
            const response = await fetch(`${API_BASE_URL}/vms/${vmName}/toggle_power?zone=${zone}&current_status=${currentStatus}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                // El cuerpo puede estar vacío si los parámetros se pasan por query string
                // body: JSON.stringify({ zone, current_status: currentStatus }), // Si el backend espera un body JSON
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || `Error al cambiar el estado de ${vmName}.`);
            }
            // Después de una operación exitosa, refrescar la lista de VMs
            await fetchVms();
            alert(`Operación de cambio de estado para ${vmName} completada.`);
        } catch (err: any) {
            console.error('Error al cambiar el estado:', err);
            setError(err.message || `Error al cambiar el estado de ${vmName}.`);
        } finally {
            setIsLoading(false);
        }
    };

    // Función para conectar a una VM (simulada por ahora)
    const handleConnect = async (vmName: string, zone: string, ipExternal: string | null) => {
        setIsLoading(true);
        setError(null);
        try {
            const response = await fetch(`${API_BASE_URL}/vms/${vmName}/connect?zone=${zone}${ipExternal ? `&ip_external=${ipExternal}` : ''}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
            });
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || `Error al intentar conectar a ${vmName}.`);
            }
            const data = await response.json();
            alert(`${data.mensaje}\nComando: ${data.comando_ssh}`);
        } catch (err: any) {
            console.error('Error al conectar:', err);
            setError(err.message || `Error al intentar conectar a ${vmName}.`);
        } finally {
            setIsLoading(false);
        }
    };

    // La función handleRefresh ahora simplemente vuelve a llamar a fetchVms
    const handleRefresh = () => {
        fetchVms();
        // Resetear filtros y búsqueda al refrescar puede ser una buena UX, o no, según preferencia
        // setSearchTerm('');
        // setStatusFilter('Todos');
        // setZoneFilter('Todas');
    };

    const filteredVms = vms
        .filter(vm => vm.name.toLowerCase().includes(searchTerm.toLowerCase()))
        .filter(vm => statusFilter === 'Todos' || vm.status === statusFilter)
        .filter(vm => zoneFilter === 'Todas' || vm.zoneRegion === zoneFilter);

    return (
        <>
            <Header />
            <FilterBar
                searchTerm={searchTerm}
                setSearchTerm={setSearchTerm}
                statusFilter={statusFilter}
                setStatusFilter={setStatusFilter}
                zoneFilter={zoneFilter}
                setZoneFilter={setZoneFilter}
                onRefresh={handleRefresh}
                zones={allZones}
            />
            <main style={styles.mainContent} role="main">
                {isLoading && <div style={styles.loadingOverlay}>Cargando VMs...</div>}
                {error && <div style={styles.errorBanner}>{error}</div>} {/* Mostrar errores al usuario */}
                <div style={styles.vmGrid} role="list">
                    {filteredVms.length > 0 ? (
                        filteredVms.map(vm => (
                            <VMCard
                                key={vm.id}
                                vm={vm}
                                // Asegúrate de pasar los parámetros necesarios a las funciones
                                onTogglePower={(id, status) => {
                                    const targetVm = vms.find(v => v.id === id);
                                    if (targetVm) {
                                        handleTogglePower(targetVm.name, targetVm.zoneRegion, status);
                                    }
                                }}
                                onConnect={(id) => {
                                    const targetVm = vms.find(v => v.id === id);
                                    if (targetVm) {
                                        handleConnect(targetVm.name, targetVm.zoneRegion, targetVm.ipExternal);
                                    }
                                }}
                            />
                        ))
                    ) : (
                        !isLoading && !error && <p style={styles.noResults}>No se encontraron VMs con los filtros aplicados.</p>
                    )}
                </div>
            </main>
        </>
    );
};

// ... (Styles and Render App - estas partes no cambian) ...

// Nuevo estilo para mensajes de error
const errorBannerStyle: React.CSSProperties = {
    backgroundColor: '#f8d7da',
    color: '#721c24',
    border: '1px solid #f5c6cb',
    borderRadius: '4px',
    padding: '10px 15px',
    margin: '10px 20px',
    textAlign: 'center',
    fontSize: '14px',
};
// Añade esto a tu objeto 'styles'
styles.errorBanner = errorBannerStyle;