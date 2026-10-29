// This is the SIP specifications of the QRhi platform support.
//
// Copyright (c) 2026 Riverbank Computing Limited <info@riverbankcomputing.com>
// 
// This file is part of PyQt6.
// 
// This file may be used under the terms of the GNU General Public License
// version 3.0 as published by the Free Software Foundation and appearing in
// the file LICENSE included in the packaging of this file.  Please review the
// following information to ensure the GNU General Public License version 3.0
// requirements will be met: http://www.gnu.org/copyleft/gpl.html.
// 
// If you do not wish to use this file under the terms of the GPL version 3.0
// then you may purchase a commercial license.  For more information contact
// info@riverbankcomputing.com.
// 
// This file is provided AS IS with NO WARRANTY OF ANY KIND, INCLUDING THE
// WARRANTY OF DESIGN, MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE.


%If (Qt_6_12_0 -)

%If (Windows)

struct QRhiD3D11InitParams : public QRhiInitParams
{
%TypeHeaderCode
#include <rhi/qrhi_platform.h>
%End

    bool enableDebugLayer;
};

struct QRhiD3D11NativeHandles : public QRhiNativeHandles
{
%TypeHeaderCode
#include <rhi/qrhi_platform.h>
%End

    qint32 adapterLuidHigh;
    quint32 adapterLuidLow;
    void *context;
    void *dev;
    int featureLevel;
};

struct QRhiD3D12CommandBufferNativeHandles : public QRhiNativeHandles
{
%TypeHeaderCode
#include <rhi/qrhi_platform.h>
%End

    void *commandList;
};

struct QRhiD3D12InitParams : public QRhiInitParams
{
%TypeHeaderCode
#include <rhi/qrhi_platform.h>
%End

    bool enableDebugLayer;
};

struct QRhiD3D12NativeHandles : public QRhiNativeHandles
{
%TypeHeaderCode
#include <rhi/qrhi_platform.h>
%End

    qint32 adapterLuidHigh;
    quint32 adapterLuidLow;
    void *commandQueue;
    void *dev;
    int minimumFeatureLevel;
};

%End


%If (PyQt_OpenGL)

struct QRhiGles2InitParams : public QRhiInitParams
{
%TypeHeaderCode
#include <rhi/qrhi_platform.h>
%End

    QRhiGles2InitParams();

    QSurface *fallbackSurface;
    QSurfaceFormat format;
    QOpenGLContext *shareContext;
    QWindow *window;

    static QOffscreenSurface *newFallbackSurface(
            const QSurfaceFormat &format = QSurfaceFormat::defaultFormat()) /Factory/;
};

struct QRhiGles2NativeHandles : public QRhiNativeHandles
{
%TypeHeaderCode
#include <rhi/qrhi_platform.h>
%End

    QOpenGLContext *context;
};

%End


%If (PyQt_Metal)

struct QRhiMetalCommandBufferNativeHandles : public QRhiNativeHandles
{
%TypeHeaderCode
#include <rhi/qrhi_platform.h>
%End

    void *commandBuffer {
%SetCode
    void *v = sipConvertToVoidPtr(sipPy);
    if (PyErr_Occurred())
        sipErr = 1;
    else
        sipCpp->commandBuffer = reinterpret_cast<MTLCommandBuffer *>(v);
%End
    };

    void *encoder {
%SetCode
    void *v = sipConvertToVoidPtr(sipPy);
    if (PyErr_Occurred())
        sipErr = 1;
    else
        sipCpp->encoder = reinterpret_cast<MTLRenderCommandEncoder *>(v);
%End
    };
};

struct QRhiMetalInitParams : public QRhiInitParams
{
%TypeHeaderCode
#include <rhi/qrhi_platform.h>
%End
};

struct QRhiMetalNativeHandles : public QRhiNativeHandles
{
%TypeHeaderCode
#include <rhi/qrhi_platform.h>
%End

    void *cmdQueue {
%SetCode
    void *v = sipConvertToVoidPtr(sipPy);
    if (PyErr_Occurred())
        sipErr = 1;
    else
        sipCpp->cmdQueue = reinterpret_cast<MTLCommandQueue *>(v);
%End
    };

    void *dev {
%SetCode
    void *v = sipConvertToVoidPtr(sipPy);
    if (PyErr_Occurred())
        sipErr = 1;
    else
        sipCpp->dev = reinterpret_cast<MTLDevice *>(v);
%End
    };
};

%End


struct QRhiNullInitParams : public QRhiInitParams
{
%TypeHeaderCode
#include <rhi/qrhi_platform.h>
%End
};

struct QRhiNullNativeHandles : public QRhiNativeHandles
{
%TypeHeaderCode
#include <rhi/qrhi_platform.h>
%End
};


%If (PyQt_Vulkan)

typedef void *VkCommandBuffer;
typedef void *VkDevice;
typedef void *VkPhysicalDevice;
typedef void *VkQueue;

// Note that this could be uint64_t if VK_USE_64_BIT_PTR_DEFINES is not
// defined.
typedef void *VkRenderPass;

struct QRhiVulkanCommandBufferNativeHandles : public QRhiNativeHandles
{
%TypeHeaderCode
#include <rhi/qrhi_platform.h>
%End

    VkCommandBuffer commandBuffer {
%SetCode
    void *v = sipConvertToVoidPtr(sipPy);
    if (PyErr_Occurred())
        sipErr = 1;
    else
        sipCpp->commandBuffer = reinterpret_cast<VkCommandBuffer>(v);
%End
    };
};

struct QRhiVulkanInitParams : public QRhiInitParams
{
%TypeHeaderCode
#include <rhi/qrhi_platform.h>
%End

    QByteArrayList deviceExtensions;
    QVulkanInstance *inst;
    QWindow *window;

    static QByteArrayList preferredInstanceExtensions();
    static QByteArrayList preferredExtensionsForImportedDevice();
};


struct QRhiVulkanNativeHandles : public QRhiNativeHandles
{
%TypeHeaderCode
#include <rhi/qrhi_platform.h>
%End

    VkDevice dev {
%SetCode
    void *v = sipConvertToVoidPtr(sipPy);
    if (PyErr_Occurred())
        sipErr = 1;
    else
        sipCpp->dev = reinterpret_cast<VkDevice>(v);
%End
    };
    VkQueue gfxQueue {
%SetCode
    void *v = sipConvertToVoidPtr(sipPy);
    if (PyErr_Occurred())
        sipErr = 1;
    else
        sipCpp->gfxQueue = reinterpret_cast<VkQueue>(v);
%End
    };
    quint32 gfxQueueFamilyIdx;
    quint32 gfxQueueIdx;
    QVulkanInstance *inst;
    VkPhysicalDevice physDev {
%SetCode
    void *v = sipConvertToVoidPtr(sipPy);
    if (PyErr_Occurred())
        sipErr = 1;
    else
        sipCpp->physDev = reinterpret_cast<VkPhysicalDevice>(v);
%End
    };
    void *vmemAllocator;
};

struct QRhiVulkanQueueSubmitParams : public QRhiNativeHandles
{
%TypeHeaderCode
#include <rhi/qrhi_platform.h>
%End

    // The three pointers are actually pointers to arrays of VkSemaphore
    // instances.
    quint32 presentWaitSemaphoreCount;
    void *presentWaitSemaphores {
%SetCode
    void *v = sipConvertToVoidPtr(sipPy);
    if (PyErr_Occurred())
        sipErr = 1;
    else
        sipCpp->presentWaitSemaphores = reinterpret_cast<VkSemaphore *>(v);
%End
    };
    quint32 waitSemaphoreCount;
    void *waitSemaphores {
%SetCode
    void *v = sipConvertToVoidPtr(sipPy);
    if (PyErr_Occurred())
        sipErr = 1;
    else
        sipCpp->waitSemaphores = reinterpret_cast<VkSemaphore *>(v);
%End
    };
    quint32 signalSemaphoreCount;
    void *signalSemaphores {
%SetCode
    void *v = sipConvertToVoidPtr(sipPy);
    if (PyErr_Occurred())
        sipErr = 1;
    else
        sipCpp->signalSemaphores = reinterpret_cast<VkSemaphore *>(v);
%End
    };
};

struct QRhiVulkanRenderPassNativeHandles : public QRhiNativeHandles
{
%TypeHeaderCode
#include <rhi/qrhi_platform.h>
%End

    VkRenderPass renderPass {
%SetCode
    void *v = sipConvertToVoidPtr(sipPy);
    if (PyErr_Occurred())
        sipErr = 1;
    else
        sipCpp->renderPass = reinterpret_cast<VkRenderPass>(v);
%End
    };
};

%End

%End
