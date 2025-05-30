from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from google.cloud import compute_v1
import os
from enum import Enum

from pydantic import BaseModel, Field, ConfigDict

app = FastAPI(
    title="GEM GCP VM Dashboard Backend",
    description="API para gestionar máquinas virtuales en Google Cloud Platform."
)

origins = [
    "http://localhost:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PROJECT_ID = "puestos-de-trabajo-potentes"

class VMStatus(str, Enum):
    RUNNING = 'Running'
    STOPPED = 'Stopped'
    PROVISIONING = 'Provisioning'

class VMResponse(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, populate_by_name=True)

    id: str
    name: str
    zoneRegion: str = Field(..., alias="zone_region")
    ipExternal: str | None = Field(None, alias="ip_external")
    ipInternal: str | None = Field(None, alias="ip_internal")
    machineType: str = Field(..., alias="machine_type")
    status: VMStatus

async def obtener_todas_las_vms_gcp():
    """Obtiene una lista de todas las máquinas virtuales en el proyecto y sus zonas."""
    vms_encontradas = []
    compute_client = compute_v1.InstancesClient()

    try:
        request = compute_v1.AggregatedListInstancesRequest(project=PROJECT_ID)
        
        # --- INICIO DE LA SIMPLIFICACIÓN EXTREMA ---
        # Solo intentar listar las instancias agregadas y devolver un mensaje de éxito simple
        # para ver si el error ocurre incluso al iterar sobre aggregated_list.items()

        aggregated_list = compute_client.aggregated_list(request=request)
        
        # Iterar solo para comprobar si la estructura básica es accesible
        for zone, scoped_list in aggregated_list.items():
            print(f"DEBUG: Procesando zona: {zone}")
            if hasattr(scoped_list, 'instances') and scoped_list.instances:
                for instance in scoped_list.instances:
                    print(f"DEBUG: Encontrada instancia: {instance.name}")
                    # Aquí ya no intentamos construir VMResponse ni acceder a atributos complejos
                    # Solo confirmamos que podemos acceder al nombre de la instancia.
                    
                    # SI ESTO FUNCIONA, EL PROBLEMA ESTÁ EN LA CONSTRUCCIÓN DE VMResponse O ACCESO A PROPIEDADES.
                    # Por ahora, devolvemos una lista de VMs simuladas si llegamos aquí
                    # para que la API responda 200 y sepamos que la conexión a GCP funcionó.
                    vms_encontradas.append(VMResponse(
                        id="debug-id",
                        name=f"debug-vm-{instance.name}",
                        zone_region=zone.split('/')[-1],
                        ipExternal="127.0.0.1",
                        ipInternal="10.0.0.1",
                        machineType="debug-type",
                        status=VMStatus.RUNNING
                    ))
                    # Limita a una sola VM para la prueba inicial si tienes muchas
                    # if len(vms_encontradas) > 0:
                    #     break
            # if len(vms_encontradas) > 0:
            #     break

        # Si no encontramos ninguna VM real pero la API no falló
        if not vms_encontradas:
            print("DEBUG: No se encontraron VMs reales o la iteración fue exitosa hasta cierto punto. Devolviendo VM de prueba.")
            vms_encontradas.append(VMResponse(
                id="000-prueba",
                name="VM-DE-PRUEBA-EXITOSA",
                zone_region="europe-west1-b",
                ipExternal="1.2.3.4",
                ipInternal="10.0.0.1",
                machineType="e2-small",
                status=VMStatus.RUNNING
            ))
        # --- FIN DE LA SIMPLIFICACIÓN EXTREMA ---

    except Exception as e:
        print(f"ERROR GLOBAL DE GCP: Falló la obtención de VMs. Detalle: {type(e).__name__}: {e}")
        # Aquí puedes añadir un pdb.set_trace() si quieres ver la traza de error en este punto
        # import pdb; pdb.set_trace()
        raise

    return vms_encontradas

# --- El resto de los endpoints y funciones (cambiar_estado_vm_gcp, toggle_power_vm, conectar_vm)
#    permanecen sin cambios en este paso de depuración.

async def cambiar_estado_vm_gcp(vm_name: str, zone: str, accion: str):
    """
    Cambia el estado de una VM (start o stop).
    :param vm_name: Nombre de la VM.
    :param zone: Zona donde se encuentra la VM.
    :param accion: 'start' para encender, 'stop' para apagar.
    """
    compute_client = compute_v1.InstancesClient()

    try:
        if accion == "start":
            operation = compute_client.start(project=PROJECT_ID, zone=zone, instance=vm_name)
        elif accion == "stop":
            operation = compute_client.stop(project=PROJECT_ID, zone=zone, instance=vm_name)
        else:
            raise ValueError("Acción no válida. Debe ser 'start' o 'stop'.")

        await operation.result()
        return {"mensaje": f"Operación '{accion}' de la VM '{vm_name}' completada exitosamente."}
    except Exception as e:
        print(f"ERROR: Falló la operación '{accion}' en la VM '{vm_name}'. Detalle: {e}")
        raise HTTPException(status_code=500, detail=f"Error al ejecutar la operación '{accion}' en la VM: {e}")


# --- Endpoints de la API ---

@app.get("/api/vms", response_model=list[VMResponse])
async def obtener_vms():
    """
    Obtiene la lista de todas las máquinas virtuales de Google Cloud Platform
    junto con su información relevante.
    """
    try:
        vms = await obtener_todas_las_vms_gcp()
        return vms
    except HTTPException as e:
        raise e
    except Exception as e: # Este catch es un fallback, la función auxiliar ya debería lanzar HTTPException
        raise HTTPException(status_code=500, detail=f"Error inesperado al obtener las VMs: {e}")

@app.post("/api/vms/{vm_name}/toggle_power")
async def toggle_power_vm(vm_name: str, zone: str, current_status: VMStatus):
    """
    Enciende o apaga una máquina virtual.
    :param vm_name: Nombre de la VM a operar.
    :param zone: Zona donde se encuentra la VM.
    :param current_status: Estado actual de la VM ('Running' o 'Stopped').
    """
    accion = ""
    if current_status == VMStatus.RUNNING:
        accion = "stop"
    elif current_status == VMStatus.STOPPED:
        accion = "start"
    elif current_status == VMStatus.PROVISIONING:
        raise HTTPException(status_code=400, detail="No se puede cambiar el estado de una VM en estado 'Provisioning'.")
    else:
        raise HTTPException(status_code=400, detail="Estado actual de VM no válido.")

    try:
        resultado = await cambiar_estado_vm_gcp(vm_name, zone, accion)
        return resultado
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error inesperado al cambiar el estado de la VM: {e}")

@app.post("/api/vms/{vm_name}/connect")
async def conectar_vm(vm_name: str, zone: str, ip_external: str | None = None):
    """
    Simula la acción de conexión a una VM, devolviendo un comando SSH.
    """
    if ip_external:
        ssh_command = f"gcloud compute ssh {vm_name} --zone={zone} --project={PROJECT_ID} --external-ip={ip_external}"
    else:
        ssh_command = f"gcloud compute ssh {vm_name} --zone={zone} --project={PROJECT_ID} # IP externa no disponible, intenta conexión interna o Cloud Shell"
    return {"mensaje": f"Para conectar a {vm_name}, usa el siguiente comando (o Cloud Shell):", "comando_ssh": ssh_command}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)